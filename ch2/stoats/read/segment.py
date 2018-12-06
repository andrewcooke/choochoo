
from math import sqrt

from .activity import ActivityImporter
from ...arty import MatchType
from ...arty.spherical import LocalTangent, SQRTree, GlobalLongitude
from ...squeal.database import add
from ...squeal.tables.segment import SegmentJournal, Segment


class SegmentImporter(ActivityImporter):

    def _on_init(self, *args, **kargs):
        super()._on_init(*args, **kargs)
        with self._db.session_context() as s:
            self.__segments = self._read_segments(s)

    def _import(self, s, path):
        ajournal, loader = super()._import(s, path)
        self._find_segments(s, ajournal,
                            loader.as_waypoints({'Latitude': 'lat',
                                                 'Longitude': 'lon',
                                                 'Distance': 'distance'}))

    def _find_segments(self, s, ajournal, waypoints):
        waypoints = [w for w in waypoints if w.lat is not None and w.lon is not None and w.distance is not None]
        self._log.debug('%d waypoints' % len(waypoints))
        candidates = self._drop_neighbours(
            sorted(self._candidates(s, waypoints), key=lambda c: (c[2].id, c[1], c[0])))
        nearest = set(self._nearest(waypoints, candidates))
        for (istart, wstart), (ifinish, wfinish), segment in self._pairs(waypoints, nearest):
            add(s, SegmentJournal(segment_id=segment.id, activity_journal=ajournal,
                                  start_time=waypoints[istart].time, start_weight=wstart,
                                  finish_time=waypoints[ifinish].time, finish_weight=wfinish))

    def _pairs(self, waypoints, nearest):
        for (da0, ia0), (da1, ia1), astart, asegment in nearest:
            for (db0, ib0), (db1, ib1), bstart, bsegment in nearest:
                if astart and not bstart:
                    if waypoints[ia1].distance < waypoints[ib0].distance:
                        if asegment == bsegment:
                            d = (waypoints[ib0].distance + waypoints[ib1].distance -
                                 (waypoints[ia0].distance + waypoints[ia1].distance)) / 2
                            if abs(d - asegment.distance) / asegment.distance < 0.1:
                                self._log.info('Found segment "%s"' % asegment.name)
                                # latest at start, earliest at end, with weights
                                yield (ia1, da0 / (da0 + da1)), (ib0, db1 / (db0 + db1)), asegment

    def _nearest(self, waypoints, candidates):

        for i, start, segment in candidates:
            plane = LocalTangent()
            xs, ys = plane.normalize(segment.coords(start))

            def neighbours():
                # need to scan a large number of points to avoid being caught at one end
                # by any candidate - but could cause issues for intervals on short circuits
                for j in range(max(0, i-20), min(len(waypoints), i+20)):
                    xw, yw = plane.normalize((waypoints[j].lon, waypoints[j].lat))
                    d = sqrt((xs - xw)**2 + (ys - yw)**2)
                    yield d, j

            candidates = sorted(neighbours())
            if candidates[0][1] > candidates[1][1]:
                # earlier first
                candidates[0], candidates[1] = candidates[1], candidates[0]
            if candidates[0][1] + 1 == candidates[1][1]:
                yield candidates[0], candidates[1], start, segment

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
                for start, id in self.__segments[[(waypoint.lon, waypoint.lat)]]:
                    segment = s.query(Segment).filter(Segment.id == id).one()
                    self._log.debug('Candidate segment "%s"' % segment.name)
                    yield i, start, segment

    def _read_segments(self, s):
        match_bounday = self._assert_karg('match_boundary', 10)
        segments = GlobalLongitude(tree=lambda: SQRTree(default_border=match_bounday, default_match=MatchType.INTERSECTS))
        for segment in s.query(Segment).all():
            segments[[segment.start]] = (True, segment.id)
            segments[[segment.finish]] = (False, segment.id)
        return segments
