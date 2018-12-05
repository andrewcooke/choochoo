
from math import sqrt

from . import WaypointCalculator
from ..names import SEGMENT_TIME, DISTANCE, LONGITUDE, LATITUDE, summaries, MIN, CNT, AVG, S
from ...arty import MatchType
from ...arty.spherical import SQRTree, LocalTangent
from ...lib.date import to_time
from ...squeal.database import add
from ...squeal.tables.segment import Segment, SegmentJournal
from ...squeal.tables.statistic import StatisticName, StatisticJournalFloat


class SegmentStatistics(WaypointCalculator):

    def __init__(self, log, db):
        super().__init__(log, db)
        with self._db.session_context() as s:
            self._rtree = self._read_segments(s)

    def _filter_journals(self, q):
        return q.filter(StatisticName.name == SEGMENT_TIME)

    def _names(self):
        return {DISTANCE: 'distance',
                LATITUDE: 'lat',
                LONGITUDE: 'lon'}

    def _add_stats_from_waypoints(self, s, ajournal, waypoints):
        candidates = self._drop_neighbours(
            sorted(self._candidates(s, waypoints), key=lambda c: (c[2].id, c[1], c[0])))
        nearest = set(self._nearest(waypoints, *candidate) for candidate in candidates)
        for pair in self._pairs(waypoints, nearest):
            self._add_stats_from_pair(s, ajournal, waypoints, *pair)

    def _add_stats_from_pair(self, s, ajournal, waypoints, start, finish, segment):
        sjournal = add(s, SegmentJournal(segment_id=segment.id, activity_journal=ajournal))
        StatisticJournalFloat.add(self._log, s, SEGMENT_TIME, S, summaries(MIN, CNT, AVG), self,
                                  sjournal, ajournal, *self._interpolate_time(waypoints, start, finish))

    def _interpolate_time(self, waypoints, start, finish):
        is0, is1, ws = start
        if0, if1, wf = finish
        return (waypoints[if0].time.timestamp() * wf + waypoints[if1].time.timestamp() * (1 - wf) -
                (waypoints[is0].time.timestamp() * ws + waypoints[is1].time.timestamp() * (1 - ws)),
                to_time(waypoints[if0].time.timestamp() * wf + waypoints[if1].time.timestamp() * (1 - wf)))

    def _pairs(self, waypoints, nearest):
        for (da0, ia0), (da1, ia1), astart, asegment in nearest:
            for (db0, ib0), (db1, ib1), bstart, bsegment in nearest:
                if astart and not bstart:
                    # import pdb; pdb.set_trace()
                    if waypoints[ia1].distance < waypoints[ib0].distance:
                        if asegment == bsegment:
                            d = (waypoints[ib0].distance + waypoints[ib1].distance -
                                 (waypoints[ia0].distance + waypoints[ia1].distance)) / 2
                            if abs(d - asegment.distance) / asegment.distance < 0.1:
                                self._log.info('Found segment "%s"' % asegment.name)
                                yield (ia0, ia1, da1 / (da0 + da1)), (ib0, ib1, db1 / (db0 + db1)), asegment

    def _nearest(self, waypoints, i, start, segment):
        plane = LocalTangent()
        xs, ys = plane.normalize(segment.coords(start))

        def neighbours():
            for j in range(max(0, i-10), min(len(waypoints), i+10)):
                xw, yw = plane.normalize((waypoints[j].lon, waypoints[j].lat))
                d = sqrt((xs - xw)**2 + (ys - yw)**2)
                yield d, j

        candidates = sorted(neighbours())
        return candidates[0], candidates[1], start, segment

    def _drop_neighbours(self, candidates, delta=2):
        prev = None
        for candidate in candidates:
            if prev is None or \
                    prev[0] != candidate[0] or prev[1] == candidate[1] or abs(prev[2] - candidate[2]) > delta:
                yield candidate
            prev = candidate

    def _candidates(self, s, waypoints):
        for i, waypoint in enumerate(waypoints):
            if waypoint.lon is not None and waypoint.lat is not None:
                # if waypoint.lon == -70.61812623403966 and waypoint.lat == -33.41535955667496:
                #     import pdb; pdb.set_trace()
                for start, id in self._rtree[[(waypoint.lon, waypoint.lat)]]:
                    segment = s.query(Segment).filter(Segment.id == id).one()
                    self._log.info('Candidate segment "%s"' % segment.name)
                    yield i, start, segment

    def _read_segments(self, s):
        # use of spherical tree means we're limited to local regions
        # in future, may need multiple trees, perhaps as leaves in a tree....
        # initial rough filter to within 10m
        rtree = SQRTree(default_border=10, default_match=MatchType.INTERSECTS)
        for segment in s.query(Segment).all():
            rtree[[segment.start]] = (True, segment.id)
            rtree[[segment.finish]] = (False, segment.id)
        return rtree
