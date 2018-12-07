
from itertools import groupby
from math import sqrt, ceil

from .activity import ActivityImporter
from ..waypoint import filter_none
from ...arty import MatchType
from ...arty.spherical import LocalTangent, SQRTree, GlobalLongitude
from ...lib.date import to_time, format_time
from ...lib.utils import sign
from ...squeal.database import add
from ...squeal.tables.segment import Segment, SegmentJournal

NAMES = {'Latitude': 'lat',
         'Longitude': 'lon',
         'Distance': 'distance'}


class CalcFailed(Exception): pass


class SegmentImporter(ActivityImporter):

    def _on_init(self, *args, **kargs):
        super()._on_init(*args, **kargs)
        with self._db.session_context() as s:
            self.__segments = self._read_segments(s)

    def _import(self, s, path):
        ajournal, loader = super()._import(s, path)
        self._find_segments(s, ajournal, filter_none(NAMES, loader.as_waypoints(NAMES)))

    def _find_segments(self, s, ajournal, waypoints):
        matches = self._initial_matches(s, waypoints)
        for _, segment_matches in groupby(matches, key=lambda m: m[2]):
            ordered = sorted(segment_matches, key=lambda m: m[0])
            coallesced = list(self._coallesce(ordered))
            starts, finishes, segment = self._split(coallesced)
            for start in reversed(starts):  # work backwards through starts
                copy = list(finishes)  # work forwards through finishes
                while copy:
                    finish = copy.pop(0)
                    if finish > start:
                        if self._try_segment(s, start, finish, waypoints, segment, ajournal):
                            finishes = finishes[:-len(copy)]  # drop this finish and later

    def _try_segment(self, s, start, finish, waypoints, segment, ajournal):
        try:
            inner = self._assert_karg('inner_bound', 5)
            outer = self._assert_karg('outer_bound', 15)
            delta = self._assert_karg('delta', 0.1)
            d = waypoints[finish].distance - waypoints[start].distance
            if abs(d - segment.distance) / segment.distance > 0.1:
                raise CalcFailed('Distance between start and finish doesn\'t match segment')
            start_time = self._end_point(start, waypoints, segment.start, inner, outer, -delta)
            finish_time = self._end_point(finish, waypoints, segment.finish, inner, outer, delta)
            add(s, SegmentJournal(segment_id=segment.id, activity_journal=ajournal,
                                  start_time=start_time, finish_time=finish_time))
            self._log.info('Added %s for %s - %s' %
                           (segment.name, format_time(start_time), format_time(finish_time)))
            return True
        except CalcFailed as e:
            self._log.warn(str(e))
            return False

    def _end_point(self, i, waypoints, p, inner, outer, delta):
        '''
        Find the time of the point that makes the segment shortest while also being at a local
        minimum in distance from the start/finish point that is within inner m.
        '''
        metric = LocalTangent(p)
        nearest = self._limit(metric, waypoints, i, p, outer, -sign(delta))
        furthest = self._limit(metric, waypoints, i, p, outer, sign(delta))
        self._log.info('Finding closest point to %s' % (p,))
        self._log.info('Rough approx - %d: %f, %d: %f, %d: %f' %
                       (nearest, self._dw(metric, p, waypoints, nearest),
                        i, self._dw(metric, p, waypoints, i),
                        furthest, self._dw(metric, p, waypoints, furthest)))
        minimum = self._minimum(metric, waypoints, nearest, furthest, delta, p, inner)
        return self._to_time(waypoints, minimum, delta)

    def _to_time(self, waypoints, i, delta):
        i0, i1, k = self._bounds(i, delta)
        return to_time(self._interpolate(waypoints[i0].time.timestamp(), waypoints[i1].time.timestamp(), k))

    def _minimum(self, metric, waypoints, nearest, furthest, delta, p, inner):
        '''
        Find the minimum within the two limits.
        '''
        i = nearest
        while True:
            i, min_d = self._next_local_minimum(metric, p, waypoints, i + delta, furthest, delta)
            self._log.info('Local minimum %.1f: %f (< %.1f?)' % (i, min_d, inner))
            if min_d < inner:
                return i

    def _next_local_minimum(self, metric, p, waypoints, i, furthest, delta):
        prev = None
        while sign(i - furthest) != sign(delta):
            i += delta
            d = self._dfrac(metric, p, waypoints, i, delta)
            if prev and prev[1] < d:
                return prev
            else:
                prev = i, d

        raise CalcFailed('No minimum found')

    def _dfrac(self, metric, p, waypoints, i, delta):
        i0, i1, k = self._bounds(i, delta)
        x0, y0 = metric.normalize((waypoints[i0].lon, waypoints[i0].lat))
        x1, y1 = metric.normalize((waypoints[i1].lon, waypoints[i1].lat))
        xk, yk = self._interpolate(x0, x1, k), self._interpolate(y0, y1, k)
        xp, yp = metric.normalize(p)
        return sqrt((xk - xp)**2 + (yk - yp)**2)

    def _bounds(self, i, delta):
        if delta > 0:
            i0, i1 = int(i), int(i) + 1
        else:
            i0, i1 = ceil(i), ceil(i) - 1
        k = (i - i0) / (i1 - i0)
        return i0, i1, k

    def _interpolate(self, a, b, k):
        return a * (1-k) + b * k

    def _limit(self, metric, waypoints, i, p, outer, delta):
        '''
        Extend i until it is more than outer away from the point.
        '''
        while self._dw(metric, p, waypoints, i) < outer:
            i += delta
        return i

    def _dw(self, metric, p, waypoints, i):
        return self._d(metric, p, (waypoints[i].lon, waypoints[i].lat))

    def _d(self, metric, p1, p2):
        '''
        The distance between two points using the given metric.
        '''
        x1, y1 = metric.normalize(p1)
        x2, y2 = metric.normalize(p2)
        return sqrt((x1 - x2)**2 + (y1 - y2)**2)

    def _split(self, coallesced):
        '''
        Split waypoints for a single segment into separate start and finish points.
        '''
        starts, finishes, segment = [], [], None
        for i, start, segment in coallesced:
            if start:
                starts.append(i)
            else:
                finishes.append(i)
        return starts, finishes, segment

    def _coallesce(self, ordered_sm):
        '''
        Combine neighbouring waypoints into a single waypoint in the middle of the black found.
        '''
        prev, first = None, None
        for match in ordered_sm:
            if prev and (prev[1:2] != match[1:2] or prev[0]+1 != match[0]):
                yield (first + prev[0]) // 2, prev[1], prev[2]
                prev, first = None, None
            if first is None:
                first = match[0]
            prev = match
        yield (first + prev[0]) // 2, prev[1], prev[2]

    def _initial_matches(self, s, waypoints):
        '''
        Check each waypoint against the r-tree and return all matches.
        '''
        for i, waypoint in enumerate(waypoints):
            for start, id in self.__segments[[(waypoint.lon, waypoint.lat)]]:
                segment = s.query(Segment).filter(Segment.id == id).one()
                self._log.debug('Candidate segment "%s"' % segment.name)
                yield i, start, segment

    def _read_segments(self, s):
        '''
        Read segment endpoints into a global R-tree so we can detect when waypoints pass nearby.
        '''
        match_bound = self._assert_karg('match_bound', 10)
        segments = GlobalLongitude(tree=lambda: SQRTree(default_border=match_bound, default_match=MatchType.INTERSECTS))
        for segment in s.query(Segment).all():
            segments[[segment.start]] = (True, segment.id)
            segments[[segment.finish]] = (False, segment.id)
        return segments
