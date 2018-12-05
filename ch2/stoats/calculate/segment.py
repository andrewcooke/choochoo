
from math import sqrt

from . import WaypointCalculator
from ..names import SEGMENT_TIME, DISTANCE, LONGITUDE, LATITUDE, summaries, MIN, CNT, AVG, S
from ...arty.spherical import SQRTree, LocalTangent
from ...squeal.database import add
from ...squeal.tables.segment import Segment, SegmentJournal
from ...squeal.tables.statistic import StatisticName, StatisticJournalFloat


class SegmentCalculator(WaypointCalculator):

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
            sorted(self._candidates(waypoints), key=lambda i, st, seg: (seg.id, st, i)))
        nearest = [self._nearest(waypoints, *candidate) for candidate in candidates]
        for pair in self._pairs(waypoints, nearest):
            self._add_stats_from_pair(s, ajournal, waypoints, *pair)

    def _add_stats_from_pair(self, s, ajournal, waypoints, start, finish, segment):
        sjournal = add(s, SegmentJournal(segment_id=segment.id, activity_journal=ajournal))
        StatisticJournalFloat.add(self._log, s, SEGMENT_TIME, S, summaries(MIN, CNT, AVG), self,
                                  sjournal, ajournal, *self._interpolate(waypoints, 'time', start, finish))

    def _interpolate(self, waypoints, attribute, start, finish):
        is0, is1, ws = start
        if0, if1, wf = finish
        return (waypoints[if0][attribute] * wf + waypoints[if1][attribute] * (1 - wf) -
                waypoints[is0][attribute] * ws + waypoints[is1][attribute] * (1 - ws),
                waypoints[if0].time * wf + waypoints[if1].time * (1 - wf))

    def _pairs(self, waypoints, nearest):
        for (da0, ia0), (da1, ia1), astart, asegment in nearest:
            for (db0, ib0), (db1, ib1), bstart, bsegment in nearest:
                if astart and not bstart and waypoints[ia1].distance < waypoints[ib0].distance \
                        and asegment == bsegment:
                    d = waypoints[ia0].distance + waypoints[ia1].distance - \
                        (waypoints[ib0].distance + waypoints[ib1].distance)
                    if abs(d - asegment.distance) / asegment.distance < 0.1:
                        yield (ia0, ia1, da1 / (da0 + da1)), (ib0, ib1, db1 / (db0 + db1)), asegment

    def _nearest(self, waypoints, i, start, segment):
        plane = LocalTangent()
        xs, ys = plane.normalize(segment.coords[start])

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

    def _candidates(self, waypoints):
        for i, waypoint in waypoints:
            for start, segment in self._rtree[(waypoint.lon, waypoint.lat)]:
                yield i, start, segment

    def _read_segments(self, s):
        # use of spherical tree means we're limited to local regions
        # in future, may need multiple trees, perhaps as leaves in a tree....
        rtree = SQRTree(border=10)  # initial rough filter to within 10m
        for segment in s.query(Segment).all():
            rtree[segment.start] = (True, segment)
            rtree[segment.finish] = (False, segment)
        return rtree
