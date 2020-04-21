
import datetime as dt
from collections import defaultdict
from json import loads
from logging import getLogger

from . import ActivityJournalCalculatorMixin, DataFrameCalculatorMixin, MultiProcCalculator
from ..names import ELEVATION, DISTANCE, M, POWER_ESTIMATE, HEART_RATE, ACTIVE_DISTANCE, MSR, SUM, CNT, MAX, \
    summaries, ACTIVE_SPEED, ACTIVE_TIME, AVG, S, KMH, MIN_KM_TIME_ANY, MIN, MED_KM_TIME_ANY, PERCENT_IN_Z_ANY, PC, \
    TIME_IN_Z_ANY, MAX_MED_HR_M_ANY, W, BPM, MAX_MEAN_PE_M_ANY, CLIMB_ELEVATION, CLIMB_DISTANCE, CLIMB_TIME, \
    CLIMB_GRADIENT, TOTAL_CLIMB, HR_ZONE, TIME, like, MEAN_POWER_ESTIMATE, ENERGY_ESTIMATE, SPHERICAL_MERCATOR_X, \
    SPHERICAL_MERCATOR_Y, DIRECTION, DEG, ASPECT_RATIO, FITNESS_D_ANY, FATIGUE_D_ANY, _delta, FF, CLIMB_POWER, \
    CLIMB_CATEGORY, KM, ALL, START, FINISH
from ...data.activity import active_stats, times_for_distance, hrz_stats, max_med_stats, max_mean_stats, \
    direction_stats, copy_times
from ...data.climb import find_climbs, Climb, add_climb_stats
from ...data.frame import activity_statistics, present, statistics
from ...data.response import response_stats
from ...lib.log import log_current_exception
from ...sql import StatisticJournalFloat, Constant, StatisticJournalText, ActivityGroup, StatisticJournalTimestamp
from ...stats.calculate.power import PowerCalculator

log = getLogger(__name__)


class ActivityCalculator(ActivityJournalCalculatorMixin, DataFrameCalculatorMixin, MultiProcCalculator):

    def __init__(self, *args, climb=None, **kargs):
        self.climb_ref = climb
        super().__init__(*args, **kargs)

    def _read_dataframe(self, s, ajournal):
        try:
            adf = activity_statistics(s, DISTANCE, ELEVATION, HEART_RATE, HR_ZONE, POWER_ESTIMATE,
                                      SPHERICAL_MERCATOR_X, SPHERICAL_MERCATOR_Y,
                                      activity_journal=ajournal, with_timespan=True, check=False)
            start, finish = ajournal.start - dt.timedelta(hours=1), ajournal.finish + dt.timedelta(hours=1)
            sdf = statistics(s, FATIGUE_D_ANY, FITNESS_D_ANY, start=start, finish=finish,
                             owner=self.owner_in, check=False)
            return adf, sdf
        except Exception as e:
            log.warning(f'Failed to generate statistics for activity: {e}')
            raise

    def _calculate_stats(self, s, ajournal, df):
        adf, sdf = df
        stats, climbs = {}, None
        stats.update(copy_times(ajournal))
        stats.update(active_stats(adf))
        stats.update(self.__average_power(s, ajournal, stats[ACTIVE_TIME]))
        stats.update(times_for_distance(adf))
        stats.update(hrz_stats(adf))
        stats.update(max_med_stats(adf))
        stats.update(max_mean_stats(adf))
        stats.update(direction_stats(adf))
        stats.update(response_stats(sdf))
        if present(adf, ELEVATION):
            params = Climb(**loads(Constant.get(s, self.climb_ref).at(s).value))
            climbs = list(find_climbs(adf, params=params))
            add_climb_stats(adf, climbs)
        return df, stats, climbs

    def __average_power(self, s, ajournal, active_time):
        # this doesn't fit nicely anywhere...
        energy = StatisticJournalFloat.at(s, ajournal.start, ENERGY_ESTIMATE, PowerCalculator, ajournal.activity_group)
        if energy and active_time:
            return {MEAN_POWER_ESTIMATE: 1000 * energy.value / active_time}
        else:
            return {MEAN_POWER_ESTIMATE: 0}

    def _copy_results(self, s, ajournal, loader, data):
        all = ActivityGroup.from_name(s, ALL)
        df, stats, climbs = data
        self.__copy(ajournal, loader, stats, START, None, None, ajournal.start, type=StatisticJournalTimestamp,
                    extra_group=all)
        self.__copy(ajournal, loader, stats, FINISH, None, None, ajournal.start, type=StatisticJournalTimestamp,
                    extra_group=all)
        self.__copy(ajournal, loader, stats, TIME, S, summaries(MAX, SUM, MSR), ajournal.start,
                    extra_group=all)
        self.__copy(ajournal, loader, stats, ACTIVE_DISTANCE, KM, summaries(MAX, CNT, SUM, MSR), ajournal.start,
                    extra_group=all)
        self.__copy(ajournal, loader, stats, ACTIVE_TIME, S, summaries(MAX, SUM, MSR), ajournal.start,
                    extra_group=all)
        self.__copy(ajournal, loader, stats, ACTIVE_SPEED, KMH, summaries(MAX, AVG, MSR), ajournal.start)
        self.__copy(ajournal, loader, stats, MEAN_POWER_ESTIMATE, W, summaries(MAX, AVG, MSR), ajournal.start)
        self.__copy(ajournal, loader, stats, DIRECTION, DEG, None, ajournal.start)
        self.__copy(ajournal, loader, stats, ASPECT_RATIO, None, None, ajournal.start)
        self.__copy_all(ajournal, loader, stats, MIN_KM_TIME_ANY, S, summaries(MIN, MSR), ajournal.start)
        self.__copy_all(ajournal, loader, stats, MED_KM_TIME_ANY, S, summaries(MIN, MSR), ajournal.start)
        self.__copy_all(ajournal, loader, stats, PERCENT_IN_Z_ANY, PC, None, ajournal.start)
        self.__copy_all(ajournal, loader, stats, TIME_IN_Z_ANY, S, None, ajournal.start)
        self.__copy_all(ajournal, loader, stats, MAX_MED_HR_M_ANY, BPM, summaries(MAX, MSR), ajournal.start)
        self.__copy_all(ajournal, loader, stats, MAX_MEAN_PE_M_ANY, W, summaries(MAX, MSR), ajournal.start)
        self.__copy_all(ajournal, loader, stats, _delta(FATIGUE_D_ANY), FF, summaries(MAX, MSR), ajournal.start)
        self.__copy_all(ajournal, loader, stats, _delta(FITNESS_D_ANY), FF, summaries(MAX, MSR), ajournal.start)
        if climbs:
            loader.add(TOTAL_CLIMB, M, summaries(MAX, MSR), ajournal.activity_group, ajournal,
                       sum(climb[CLIMB_ELEVATION] for climb in climbs), ajournal.start, StatisticJournalFloat,
                       description=DESCRIPTIONS[TOTAL_CLIMB])
            for climb in sorted(climbs, key=lambda climb: climb[TIME]):
                self.__copy(ajournal, loader, climb, CLIMB_ELEVATION, M, summaries(MAX, SUM, MSR), climb[TIME])
                self.__copy(ajournal, loader, climb, CLIMB_DISTANCE, KM, summaries(MAX, SUM, MSR), climb[TIME])
                self.__copy(ajournal, loader, climb, CLIMB_TIME, S, summaries(MAX, SUM, MSR), climb[TIME])
                self.__copy(ajournal, loader, climb, CLIMB_GRADIENT, PC, summaries(MAX, MSR), climb[TIME])
                self.__copy(ajournal, loader, climb, CLIMB_POWER, W, summaries(MAX, MSR), climb[TIME])
                if CLIMB_CATEGORY in climb:
                    self.__copy(ajournal, loader, climb, CLIMB_CATEGORY, None, None, climb[TIME],
                                type=StatisticJournalText)
        if stats:
            log.warning(f'Unsaved statistics: {list(stats.keys())}')

    def __copy_all(self, ajournal, loader, stats, pattern, units, summary, time, type=StatisticJournalFloat):
        description = DESCRIPTIONS[pattern]
        for name in like(pattern, stats):
            self.__copy(ajournal, loader, stats, name, units, summary, time, type=type, description=description)

    def __copy(self, ajournal, loader, stats, name, units, summary, time, type=StatisticJournalFloat,
               extra_group=None, description=None):
        if not description: description = DESCRIPTIONS[name]
        groups = [ajournal.activity_group]
        if extra_group: groups += [extra_group]
        for group in groups:
            try:
                loader.add(name, units, summary, group, ajournal, stats[name], time, type, description=description)
            except:
                log.warning(f'Failed to load {name}')
                log_current_exception(traceback=False)
        del stats[name]


DESCRIPTIONS = defaultdict(lambda: None, {
    START: '''The start time for the activity.''',
    FINISH: '''The finish time for the activity.''',
    TIME: '''The total duration of the activity.''',
    ACTIVE_DISTANCE: '''The total distance travelled while active (ie not paused).''',
    ACTIVE_TIME: '''The total time while active (ie not paused).''',
    ACTIVE_SPEED: '''The average speed while active (ie not paused).''',
    MEAN_POWER_ESTIMATE: '''The average estimated power.''',
    DIRECTION: '''The angular direction (clockwise from North) of the mid-point of teh activity relative to the start.''',
    ASPECT_RATIO: f'''The relative extent of the activity along and across the {DIRECTION}.''',
    MIN_KM_TIME_ANY: '''The shortest time required to cover the given distance.''',
    MED_KM_TIME_ANY: '''The median(typical) time required to cover the given distance.''',
    PERCENT_IN_Z_ANY: '''The percentage of time in the given HR zone.''',
    TIME_IN_Z_ANY: '''The total time in the given HR zone.''',
    MAX_MED_HR_M_ANY: '''The highest median HR in the given interval.''',
    MAX_MEAN_PE_M_ANY: '''The highest average power estimate in the given interval.''',
    _delta(FATIGUE_D_ANY): '''The change (over the activity) in the SHRIMP Fatigue parameter.''',
    _delta(FITNESS_D_ANY): '''The change (over the activity) in the SHRIMP Fitness parameter.''',
    TOTAL_CLIMB: '''The total height climbed in the detected climbs (only).''',
    CLIMB_ELEVATION: '''The difference in elevation between start and end of the climb.''',
    CLIMB_DISTANCE: '''The distance travelled during the climb''',
    CLIMB_TIME: '''The time spent on the climb.''',
    CLIMB_GRADIENT: '''The average inclination of the climb (elevation / distance).''',
    CLIMB_POWER: '''The average estimated power during the climb.''',
    CLIMB_CATEGORY: '''The climb category.'''
})