
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
        self._find_segments(s, ajournal, filter_none(NAMES.values(), loader.as_waypoints(NAMES)))

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

    def _try_segment(self, s, starts, finishes, waypoints, segment, ajournal):
        try:
            inner = self._assert_karg('inner_bound', 5)
            d = waypoints[self._mid(finishes)].distance - waypoints[self._mid(starts)].distance
            if abs(d - segment.distance) / segment.distance > 0.1:
                raise CalcFailed('Distance between start and finish doesn\'t match segment')
            start_time = self._end_point(starts, waypoints, segment.start, inner, True)
            finish_time = self._end_point(finishes, waypoints, segment.finish, inner, False)
            add(s, SegmentJournal(segment_id=segment.id, activity_journal=ajournal,
                                  start=start_time, finish=finish_time))
            self._log.info('Added %s for %s - %s' %
                           (segment.name, format_time(start_time), format_time(finish_time)))
            return True
        except CalcFailed as e:
            self._log.warn(str(e))
            return False

    def _mid(self, indices):
        n = len(indices)
        return indices[n // 2]

    def _end_point(self, indices, waypoints, p, inner, hi_to_lo):
        '''
        Find the time of the point that makes the segment shortest while also being at a local
        minimum in distance from the start/finish point that is within inner m.
        '''
        metric = LocalTangent(p)
        lo, hi = self._limits(metric, waypoints, indices, p)
        self._log.info('Finding closest point to %s within %d: %f, %d: %f' %
                       (p, lo, self._dw(metric, p, waypoints, lo),
                        hi, self._dw(metric, p, waypoints, hi)))
        if hi_to_lo:
            start, finish = hi, lo
        else:
            start, finish = lo, hi
        minimum = self._minimum(metric, waypoints, start, finish, p, inner)
        return self._to_time(waypoints, minimum)

    def _to_time(self, waypoints, i):
        i0, i1, k = self._bounds(i)
        return to_time(self._interpolate(waypoints[i0].time.timestamp(), waypoints[i1].time.timestamp(), k))

    def _minimum(self, metric, waypoints, start, finish, p, inner):
        '''
        Find the minimum within the two limits.
        '''
        i = start
        while True:
            i, min_d = self._next_local_minimum(metric, p, waypoints, i, start, finish)
            self._log.info('Local minimum %.1f: %f (< %.1f?)' % (i, min_d, inner))
            if min_d < inner:
                return i
            if start < finish:
                i = int(i + 1)
            else:
                i = ceil(i - 1)

    def _next_local_minimum(self, metric, p, waypoints, i, start, finish):
        # import pdb; pdb.set_trace()
        # this from basic algebra (too long for a comment)
        # p0 is the point we want to minimize distance to
        # pi and pj are the end points of a nearby line segment
        # k is the fractional distance between pi and pj for the point nearest to p0
        # things are complicated by the need to return pj if it's the nearest point (discontinuity)
        p0 = metric.normalize(p)
        pi = metric.normalize((waypoints[i].lon, waypoints[i].lat))
        prev_discontinuity = None
        while start <= i < finish or start >= i > finish:
            j = i + sign(finish - start)
            pj = metric.normalize((waypoints[j].lon, waypoints[j].lat))
            dxji, dyji = pj[0] - pi[0], pj[1] - pi[1]
            dx0i, dy0i = p0[0] - pi[0], p0[1] - pi[1]
            k = (dxji * dx0i + dyji * dy0i) / (dxji**2 + dyji**2)
            if 0 < k < 1:  # we have a solution within the segment
                p1 = (pi[0] + k * (pj[0] - pi[0]), pi[1] + k * (pj[1] - pi[1]))
                return i + k * sign(finish - start), sqrt((p0[0] - p1[0])**2 + (p0[1] - p1[1])**2)
            # are we moving towards the target?
            if k > 1:
                # if so, save this endpoint as a possible minimum
                prev_discontinuity = (j, self._dw(metric, p, waypoints, j))
            else:
                # if not, then if we were before it was a minimum
                if prev_discontinuity:
                    return prev_discontinuity
            i, pi = j, pj
        raise CalcFailed('No minimum found')

    def _dfrac(self, metric, p, waypoints, i, delta):
        i0, i1, k = self._bounds(i, delta)
        x0, y0 = metric.normalize((waypoints[i0].lon, waypoints[i0].lat))
        x1, y1 = metric.normalize((waypoints[i1].lon, waypoints[i1].lat))
        xk, yk = self._interpolate(x0, x1, k), self._interpolate(y0, y1, k)
        xp, yp = metric.normalize(p)
        return sqrt((xk - xp)**2 + (yk - yp)**2)

    def _bounds(self, i):
        i0, i1 = int(i), int(i) + 1
        k = (i - i0) / (i1 - i0)
        return i0, i1, k

    def _interpolate(self, a0, a1, k):
        return a0 * (1 - k) + a1 * k

    def _limits(self, metric, waypoints, indices, p):
        lo, hi = indices
        if lo == hi:
            lo, hi = lo-1, hi+1
        dl, dh = self._dw(metric, p, waypoints, lo), self._dw(metric, p, waypoints, hi)
        if dl < dh:
            lo, dl = self._inc_limit(metric, waypoints, p, dl, dh, lo, -1)
            hi, dh = self._inc_limit(metric, waypoints, p, dh, dl, hi, 1)
        else:
            hi, dh = self._inc_limit(metric, waypoints, p, dh, dl, hi, 1)
            lo, dl = self._inc_limit(metric, waypoints, p, dl, dh, lo, -1)
        self._log.info('Expanded %s to %s' % (indices, (lo, hi)))
        return lo, hi

    def _inc_limit(self, metric, waypoints, p, da, db, a, inc):
        while da < db and ((inc > 0 and a < len(waypoints) - 1) or (inc < 0 and a > 0)):
            a += inc
            da = self._dw(metric, p, waypoints, a)
        return a, da

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
        Replace contiguous ranges of waypoints with a pair (min, max)
        '''
        prev, first = None, None
        for match in ordered_sm:
            if prev and (prev[1:2] != match[1:2] or prev[0]+1 != match[0]):
                yield (first, prev[0]), prev[1], prev[2]
                prev, first = None, None
            if first is None:
                first = match[0]
            prev = match
        yield (first, prev[0]) , prev[1], prev[2]

    def _initial_matches(self, s, waypoints):
        '''
        Check each waypoint against the r-tree and return all matches.
        '''
        found = set()
        for i, waypoint in enumerate(waypoints):
            for start, id in self.__segments[[(waypoint.lon, waypoint.lat)]]:
                segment = s.query(Segment).filter(Segment.id == id).one()
                if segment not in found:
                    self._log.info('Candidate segment "%s"' % segment.name)
                    found.add(segment)
                yield i, start, segment

    def _read_segments(self, s):
        '''
        Read segment endpoints into a global R-tree so we can detect when waypoints pass nearby.
        '''
        match_bound = self._assert_karg('match_bound', 25)
        segments = GlobalLongitude(tree=lambda: SQRTree(default_border=match_bound, default_match=MatchType.INTERSECTS))
        for segment in s.query(Segment).all():
            segments[[segment.start]] = (True, segment.id)
            segments[[segment.finish]] = (False, segment.id)
        if not segments:
            self._log.warn('No segments defined in database')
        return segments
