
from collections import Counter
from itertools import chain
from operator import lt, gt

from . import WaypointCalculator
from .heart_rate import hr_zones_from_database
from ..names import ACTIVE_DISTANCE, MAX, M, ACTIVE_TIME, S, ACTIVE_SPEED, KMH, round_km, MEDIAN_KM_TIME, \
    PERCENT_IN_Z, PC, TIME_IN_Z, HR_MINUTES, MAX_MED_HR_M, BPM, MIN, CNT, SUM, AVG, MSR, summaries, HEART_RATE, \
    DISTANCE, ELEVATION
from ..waypoint import Chunks
from ...squeal import StatisticName


class ActivityStatistics(WaypointCalculator):

    def _filter_statistic_journals(self, q):
        return q.filter(StatisticName.name == ACTIVE_TIME)

    def _names(self):
        return {HEART_RATE: 'heart_rate',
                DISTANCE: 'distance',
                ELEVATION: 'elevation'}

    def _add_stats_from_waypoints(self, s, ajournal, waypoints):
        totals = Totals(self._log, waypoints)
        self._add_float_stat(s, ajournal,  ACTIVE_DISTANCE, summaries(MAX, CNT, SUM, MSR), totals.distance, M)
        self._add_float_stat(s, ajournal, ACTIVE_TIME, summaries(MAX, SUM, MSR), totals.time, S)
        self._add_float_stat(s, ajournal, ACTIVE_SPEED, summaries(MAX, AVG, MSR), totals.distance * 3.6 / totals.time, KMH)
        for target in round_km():
            times = list(sorted(TimeForDistance(self._log, waypoints, target * 1000).times()))
            if not times:
                break
            median = len(times) // 2
            self._add_float_stat(s, ajournal, MEDIAN_KM_TIME % target, summaries(MIN, MSR), times[median], S)
        zones = hr_zones_from_database(self._log, s, ajournal.activity_group, ajournal.start)
        if zones:
            for (zone, frac) in Zones(self._log, waypoints, zones).zones:
                self._add_float_stat(s, ajournal, PERCENT_IN_Z % zone, None, 100 * frac, PC)
            # for (zone, frac) in Zones(self._log, waypoints, zones).zones:
                self._add_float_stat(s, ajournal, TIME_IN_Z % zone, None, frac * totals.time, S)
            for target in HR_MINUTES:
                heart_rates = sorted(MedianHRForTime(self._log, waypoints, target * 60).heart_rates(), reverse=True)
                if heart_rates:
                    self._add_float_stat(s, ajournal, MAX_MED_HR_M % target, summaries(MAX, MSR), heart_rates[0], BPM)
        else:
            self._log.warning('No HR zones defined for %s or before' % ajournal.start)


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
