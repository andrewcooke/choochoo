
from . import WaypointCalculator
from .waypoint import Chunks
from ..names import SEGMENT_TIME
from ...arty import LQRTree
from ...squeal.tables.segment import Segment
from ...squeal.tables.statistic import StatisticName


class SegmentCalculator(WaypointCalculator):

    def __init__(self, log, db):
        super().__init__(log, db)
        with self._db.session_context() as s:
            self._rtree, self._segments = self._read_segments(s)

    def _filter_journals(self, q):
        return q.filter(StatisticName.name == SEGMENT_TIME)

    def _add_stats_from_waypoints(self, s, ajournal, waypoints):
        pass

    def _read_segments(self, s):
        rtree = LQRTree()
        segments = []
        for segment in s.query(Segment).all():
            rtree.add(segment.start, segment.id, border=segment.border)
            segments.append(segment)
        return rtree, segments


class TimeForDistance(Chunks):

    def __init__(self, log, waypoints, distance):
        super().__init__(log, waypoints)
        self.__distance = distance

    def times(self):
        for chunks in self.chunks():
            distance = sum(chunk.distance() for chunk in chunks)
            if distance > self.__distance:
                while chunks and distance - chunks[0].distance_delta() > self.__distance:
                    distance -= chunks[0].distance_delta()
                    self.drop_first(chunks)
                time = sum(chunk.time() for chunk in chunks)
                yield time * self.__distance / distance
