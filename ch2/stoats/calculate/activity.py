
from collections import Counter
from itertools import chain
from json import loads

from scipy.interpolate import UnivariateSpline

from . import WaypointCalculator
from .climb import find_climbs, Climb
from .heart_rate import hr_zones_from_database
from ..load import StatisticJournalLoader
from ..names import *
from ..waypoint import Chunks
from ...squeal import Constant, StatisticName, StatisticJournalFloat, StatisticJournalInteger

HR_MINUTES = (5, 10, 15, 20, 30, 60, 90, 120, 180)


def round_km():
    yield from range(5, 21, 5)
    yield from range(25, 76, 25)
    yield from range(100, 251, 50)
    yield from range(300, 1001, 100)


class ActivityStatistics(WaypointCalculator):

    # for historical reasons, and because it adds few stats, this still doesn't use a loader.

    def _run_activity(self, s, activity_group):
        climb = self._assert_karg('climb')
        self.__climb = Climb(**loads(Constant.get(s, climb).at(s).value))
        return super()._run_activity(s, activity_group)

    def _filter_statistic_journals(self, q):
        return q.filter(StatisticName.name == ACTIVE_TIME)

    def _names(self):
        names = {HEART_RATE: 'heart_rate',
                 DISTANCE: 'distance',
                 RAW_ELEVATION: 'raw_elevation',
                 ELEVATION: 'elevation'}
        return names

    def _add_float_stat(self, s, ajournal, name, summary, value, units, time=None):
        if time is None:
            time = ajournal.start
        StatisticJournalFloat.add(self._log, s, name, units, summary, ActivityStatistics,
                                  ajournal.activity_group, ajournal, value, time)

    def _add_int_stat(self, s, ajournal, name, summary, value, units, time=None):
        if time is None:
            time = ajournal.start
        StatisticJournalInteger.add(self._log, s, name, units, summary, ActivityStatistics,
                                    ajournal.activity_group, ajournal, int(round(value)), time)

    def _add_stats_from_waypoints(self, s, ajournal, waypoints):
        totals = self._add_totals(s, ajournal, waypoints)
        self._add_times_for_distance(s, ajournal, waypoints)
        self._add_hr_stats(s, ajournal, waypoints, totals)
        waypoints = self._fix_elevation(s, ajournal, waypoints)
        self._add_climbs(s, ajournal, waypoints)

    def _add_totals(self, s, ajournal, waypoints):
        totals = Totals(self._log, waypoints)
        self._add_float_stat(s, ajournal, ACTIVE_DISTANCE, summaries(MAX, CNT, SUM, MSR), totals.distance, M)
        self._add_float_stat(s, ajournal, ACTIVE_TIME, summaries(MAX, SUM, MSR), totals.time, S)
        self._add_float_stat(s, ajournal, ACTIVE_SPEED, summaries(MAX, AVG, MSR), totals.distance * 3.6 / totals.time, KMH)
        return totals

    def _add_times_for_distance(self, s, ajournal, waypoints):
        for target in round_km():
            times = list(sorted(TimeForDistance(self._log, waypoints, target * 1000).times()))
            if not times:
                break
            median = len(times) // 2
            self._add_float_stat(s, ajournal, MEDIAN_KM_TIME % target, summaries(MIN, MSR), times[median], S)

    def _add_hr_stats(self, s, ajournal, waypoints, totals):
        zones = hr_zones_from_database(self._log, s, ajournal.activity_group, ajournal.start)
        if zones:
            for (zone, frac) in Zones(self._log, waypoints, zones).zones:
                self._add_float_stat(s, ajournal, PERCENT_IN_Z % zone, None, 100 * frac, PC)
                self._add_float_stat(s, ajournal, TIME_IN_Z % zone, None, frac * totals.time, S)
            for target in HR_MINUTES:
                heart_rates = sorted(MedianHRForTime(self._log, waypoints, target * 60).heart_rates(), reverse=True)
                if heart_rates:
                    self._add_float_stat(s, ajournal, MAX_MED_HR_M % target, summaries(MAX, MSR), heart_rates[0], BPM)
        else:
            self._log.warning('No HR zones defined for %s or before' % ajournal.start)

    def _fix_elevation(self, s, ajournal, waypoints):
        with_elevations = [waypoint for waypoint in waypoints if waypoint.raw_elevation != None]
        if len(with_elevations) > 4:
            fixed = []
            x = [waypoint.distance for waypoint in with_elevations]
            y = [waypoint.raw_elevation for waypoint in with_elevations]
            i = 1
            while i < len(x):
                if x[i-1] >= x[i]:
                    del x[i-1], y[i-1]
                else:
                    i += 1
            loader = StatisticJournalLoader(self._log, s, self)
            # the 7 here is from eyeballing various plots compared to other values
            # it seems better to smooth along the route rather that smooth the terrain model since
            # 1 - we expect the route to be smoother than the terrain in general (roads / tracks)
            # 2 - smoothing the 2d terrain is difficult to control and can give spikes
            # 3 - we better handle errors from mismatches between terrain model and position
            #     (think hairpin bends going up a mountainside)
            # the main drawbacks are
            # 1 - speed on loading
            # 2 - no guarantee of consistency between routes (or even on the same routine retracing a path)
            spline = UnivariateSpline(x, y, s=len(with_elevations) * 7)
            for waypoint in with_elevations:
                elevation = spline(waypoint.distance)
                loader.add(ELEVATION, M, None, ajournal.activity_group, ajournal,
                           elevation, waypoint.time, StatisticJournalFloat)
                fixed.append(waypoint._replace(elevation=elevation))
            loader.load()
            return fixed
        else:
            return waypoints

    def _add_climbs(self, s, ajournal, waypoints):
        total_elevation = 0
        for lo, hi in find_climbs(waypoints, params=self.__climb):
            up = hi.elevation - lo.elevation
            along = hi.distance - lo.distance
            time = (hi.time - lo.time).total_seconds()
            self._add_float_stat(s, ajournal, CLIMB_ELEVATION, summaries(MAX, SUM, MSR), up, M, time=hi.time)
            self._add_float_stat(s, ajournal, CLIMB_DISTANCE, summaries(MAX, SUM, MSR), along, M, time=hi.time)
            self._add_float_stat(s, ajournal, CLIMB_TIME, summaries(MAX, SUM, MSR), time, S, time=hi.time)
            self._add_float_stat(s, ajournal, CLIMB_GRADIENT, summaries(MAX, MSR), 100 * up / along, PC, time=hi.time)
            total_elevation += up
        if total_elevation:
            self._add_float_stat(s, ajournal, TOTAL_CLIMB, summaries(MAX, SUM, MSR), total_elevation, M)


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


class MedianHRForTime(Chunks):

    def __init__(self, log, waypoints, time, max_gap=None):
        super().__init__(log, waypoints)
        self.__time = time
        self.__max_gap = 0.01 * time if max_gap is None else max_gap
        log.debug('Will reject gaps > %ds' % int(self.__max_gap))

    def _max_gap(self, chunks):
        return max(c1[0].timespan.start - c2[0].timespan.finish
                   for c1, c2 in zip(list(chunks)[1:], chunks)).total_seconds()

    def heart_rates(self):
        for chunks in self.chunks():
            while len(chunks) > 1 and self._max_gap(chunks) > self.__max_gap:
                self._log.debug('Rejecting chunk because of gap (%ds)' % int(self._max_gap(chunks)))
                chunks.popleft()
            time = sum(chunk.time() for chunk in chunks)
            if time > self.__time:
                while chunks and time - chunks[0].time_delta() > self.__time:
                    time -= chunks[0].time_delta()
                    self.drop_first(chunks)
                heart_rates = list(sorted(chain(*(chunk.heart_rates() for chunk in chunks))))
                if heart_rates:
                    median = len(heart_rates) // 2
                    yield heart_rates[median]


class Totals(Chunks):

    def __init__(self, log, waypoints):
        super().__init__(log, waypoints)
        all_chunks = self.complete()
        self.distance = sum(chunk.distance() for chunk in all_chunks)
        self.time = sum(chunk.time() for chunk in all_chunks)


class Zones(Chunks):

    def __init__(self, log, waypoints, zones):
        super().__init__(log, waypoints)
        # this assumes record data are evenly distributed
        self.zones = []
        all_chunks = self.complete()
        counts = Counter()
        lower_limit = 0
        for zone, upper_limit in enumerate(zones):
            for chunk in all_chunks:
                for heart_rate in chunk.heart_rates():
                    if heart_rate is not None:
                        if lower_limit <= heart_rate < upper_limit:
                            counts[zone] += 1  # zero-based (incremented below)
            lower_limit = upper_limit
        total = sum(counts.values())
        if total:
            for zone in range(len(zones)):
                self.zones.append((zone + 1, counts[zone] / total))

