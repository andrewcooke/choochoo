
from collections import Counter
from itertools import chain
from json import loads
from logging import getLogger

from . import MultiProcCalculator, ActivityJournalCalculatorMixin, WaypointCalculatorMixin
from ..names import *
from ..waypoint import Chunks
from ...data.climb import find_climbs, Climb
from ...lib.data import MaxDict
from ...squeal import Constant, StatisticJournalFloat
from ...stoats.calculate.heart_rate import hr_zones_from_database

log = getLogger(__name__)
MAX_MED_MINUTES = (5, 10, 30, 60, 90, 120, 180)


def round_km():
    yield from range(5, 21, 5)
    yield from range(25, 76, 25)
    yield from range(100, 251, 50)
    yield from range(300, 1001, 100)


class TimeForDistance(Chunks):

    def __init__(self, waypoints, distance):
        super().__init__(waypoints)
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

    def __init__(self, waypoints, time, max_gap=None):
        super().__init__(waypoints)
        self.__time = time
        self.__max_gap = 0.01 * time if max_gap is None else max_gap
        log.debug('Will reject gaps > %ds' % int(self.__max_gap))

    def _max_gap(self, chunks):
        return max(c1[0].timespan.start - c2[0].timespan.finish
                   for c1, c2 in zip(list(chunks)[1:], chunks)).total_seconds()

    def heart_rates(self):
        for chunks in self.chunks():
            while len(chunks) > 1 and self._max_gap(chunks) > self.__max_gap:
                log.debug('Rejecting chunk because of gap (%ds)' % int(self._max_gap(chunks)))
                chunks.popleft()
            time = sum(chunk.time() for chunk in chunks)
            if time > self.__time:
                while chunks and time - chunks[0].time_delta() > self.__time:
                    time -= chunks[0].time_delta()
                    self.drop_first(chunks)
                heart_rates = list(sorted(chain(*(chunk.values('heart_rate') for chunk in chunks))))
                if heart_rates:
                    median = len(heart_rates) // 2
                    yield heart_rates[median]


class MedianForTime(Chunks):

    def __init__(self, waypoints, time, max_gap=None):
        super().__init__(waypoints)
        self.__time = time
        self.__max_gap = 0.01 * time if max_gap is None else max_gap
        log.debug('Will reject gaps > %ds' % int(self.__max_gap))

    def _max_gap(self, chunks):
        return max(c1[0].timespan.start - c2[0].timespan.finish
                   for c1, c2 in zip(list(chunks)[1:], chunks)).total_seconds()

    def values(self, *names):
        for chunks in self.chunks():
            while len(chunks) > 1 and self._max_gap(chunks) > self.__max_gap:
                log.debug('Rejecting chunk because of gap (%ds)' % int(self._max_gap(chunks)))
                chunks.popleft()
            time = sum(chunk.time() for chunk in chunks)
            if time > self.__time:
                while chunks and time - chunks[0].time_delta() > self.__time:
                    time -= chunks[0].time_delta()
                    self.drop_first(chunks)
                for name in names:
                    values = list(sorted(chain(*(chunk.values(name) for chunk in chunks))))
                    if values:
                        median = len(values) // 2
                        yield name, values[median]


class Totals(Chunks):

    def __init__(self, waypoints):
        super().__init__(waypoints)
        all_chunks = self.complete()
        self.distance = sum(chunk.distance() for chunk in all_chunks)
        self.time = sum(chunk.time() for chunk in all_chunks)


class Zones(Chunks):

    def __init__(self, waypoints, zones):
        super().__init__(waypoints)
        # this assumes record data are evenly distributed
        self.zones = []
        all_chunks = self.complete()
        counts = Counter()
        lower_limit = 0
        for zone, upper_limit in enumerate(zones):
            for chunk in all_chunks:
                for heart_rate in chunk.values('heart_rate'):
                    if heart_rate is not None:
                        if lower_limit <= heart_rate < upper_limit:
                            counts[zone] += 1  # zero-based (incremented below)
            lower_limit = upper_limit
        total = sum(counts.values())
        if total:
            for zone in range(len(zones)):
                self.zones.append((zone + 1, counts[zone] / total))


class ActivityCalculator(ActivityJournalCalculatorMixin, WaypointCalculatorMixin, MultiProcCalculator):

    def __init__(self, *args, cost_calc=10, cost_write=1, climb=None, **kargs):
        self.climb_ref = climb
        super().__init__(*args, cost_calc=cost_calc, cost_write=cost_write, **kargs)

    def _names(self):
        return {HEART_RATE: 'heart_rate',
                DISTANCE: 'distance',
                ELEVATION: 'elevation',
                POWER_ESTIMATE: 'power_estimate'}

    def _get_loader(self, s):
        # no serial because we timetravel below
        return super()._get_loader(s, add_serial=False)

    def _calculate_results(self, s, ajournal, waypoints, loader):
        totals = self._add_totals(s, ajournal, waypoints, loader)
        self._add_times_for_distance(s, ajournal, waypoints, loader)
        self._add_hrz_stats(s, totals, ajournal, waypoints, loader)
        self._add_max_med_stats(s, totals, ajournal, waypoints, loader)
        self._add_climbs(s, ajournal, waypoints, loader)

    def _add_totals(self, s, ajournal, waypoints, loader):
        totals = Totals(waypoints)
        loader.add(ACTIVE_DISTANCE, M, summaries(MAX, CNT, SUM, MSR), ajournal.activity_group, ajournal,
                   totals.distance, ajournal.start, StatisticJournalFloat)
        loader.add(ACTIVE_TIME, S, summaries(MAX, SUM, MSR), ajournal.activity_group, ajournal,
                   totals.time, ajournal.start, StatisticJournalFloat)
        loader.add(ACTIVE_SPEED, KMH, summaries(MAX, AVG, MSR), ajournal.activity_group, ajournal,
                   totals.distance * 3.6 / totals.time, ajournal.start, StatisticJournalFloat)
        return totals

    def _add_times_for_distance(self, s, ajournal, waypoints, loader):
        for target in round_km():
            times = list(sorted(TimeForDistance(waypoints, target * 1000).times()))
            if not times:
                break
            loader.add(MIN_KM_TIME % target, S, summaries(MIN, MSR), ajournal.activity_group, ajournal,
                       times[0], ajournal.start, StatisticJournalFloat)
            median = len(times) // 2
            loader.add(MED_KM_TIME % target, S, summaries(MIN, MSR), ajournal.activity_group, ajournal,
                       times[median], ajournal.start, StatisticJournalFloat)

    def _add_hrz_stats(self, s, totals, ajournal, waypoints, loader):
        zones = hr_zones_from_database(s, ajournal.activity_group, ajournal.start)
        if zones:
            for (zone, frac) in Zones(waypoints, zones).zones:
                loader.add(PERCENT_IN_Z % zone, PC, None, ajournal.activity_group, ajournal,
                           100 * frac, ajournal.start, StatisticJournalFloat)
                loader.add(TIME_IN_Z % zone, S, None, ajournal.activity_group, ajournal,
                           frac * totals.time, ajournal.start, StatisticJournalFloat)
        else:
            log.warning('No HR zones defined for %s or before' % ajournal.start)

    def _add_max_med_stats(self, s, totals, ajournal, waypoints, loader):
        for target in MAX_MED_MINUTES:
            maxes = MaxDict(MedianForTime(waypoints, target * 60).values('heart_rate', 'power_estimate'))
            if 'heart_rate' in maxes:
                loader.add(MAX_MED_HR_M % target, BPM, summaries(MAX, MSR), ajournal.activity_group, ajournal,
                           maxes['heart_rate'], ajournal.start, StatisticJournalFloat)
            if 'power_estimate' in maxes:
                loader.add(MAX_MED_EP_M % target, W, summaries(MAX, MSR), ajournal.activity_group, ajournal,
                           maxes['power_estimate'], ajournal.start, StatisticJournalFloat)

    def _add_climbs(self, s, ajournal, waypoints, loader):
        climb = Climb(**loads(Constant.get(s, self.climb_ref).at(s).value))
        total_elevation = 0
        for lo, hi in find_climbs(waypoints, params=climb):
            up = hi.elevation - lo.elevation
            along = hi.distance - lo.distance
            time = (hi.time - lo.time).total_seconds()
            loader.add(CLIMB_ELEVATION, M, summaries(MAX, SUM, MSR), ajournal.activity_group, ajournal,
                       up, hi.time, StatisticJournalFloat)
            loader.add(CLIMB_DISTANCE, M, summaries(MAX, SUM, MSR), ajournal.activity_group, ajournal,
                       along, hi.time, StatisticJournalFloat)
            loader.add(CLIMB_TIME, S, summaries(MAX, SUM, MSR), ajournal.activity_group, ajournal,
                       time, hi.time, StatisticJournalFloat)
            loader.add(CLIMB_GRADIENT, PC, summaries(MAX, SUM, MSR), ajournal.activity_group, ajournal,
                       100 * up / along, hi.time, StatisticJournalFloat)
            total_elevation += up
        if total_elevation:
            loader.add(TOTAL_CLIMB, M, summaries(MAX, SUM, MSR), ajournal.activity_group, ajournal,
                       total_elevation, ajournal.start, StatisticJournalFloat)

