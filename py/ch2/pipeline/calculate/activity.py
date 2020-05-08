
import datetime as dt
from collections import defaultdict
from json import loads
from logging import getLogger

from sqlalchemy import desc

from .calculate import MultiProcCalculator, ActivityJournalCalculatorMixin, DataFrameCalculatorMixin
from .power import PowerCalculator
from ...data.activity import active_stats, times_for_distance, hrz_stats, max_med_stats, max_mean_stats, \
    direction_stats, copy_times
from ...data.climb import find_climbs, Climb, add_climb_stats
from ...data.frame import activity_statistics, present, statistics
from ...data.response import response_stats
from ...lib import time_to_local_time
from ...lib.log import log_current_exception
from ...names import Names as N, Titles as T, Summaries as S, Units, titles_for_names
from ...sql import StatisticJournalFloat, Constant, StatisticJournalText, ActivityGroup, StatisticJournalTimestamp, \
    ActivityJournal
from ...sql.types import simple_name

log = getLogger(__name__)


class ActivityCalculator(ActivityJournalCalculatorMixin, DataFrameCalculatorMixin, MultiProcCalculator):

    def __init__(self, *args, climb=None, **kargs):
        self.climb_ref = climb
        super().__init__(*args, **kargs)

    def _read_dataframe(self, s, ajournal):
        try:
            adf = activity_statistics(s, N.DISTANCE, N.ELEVATION, N.HEART_RATE, N.HR_ZONE,
                                      N.POWER_ESTIMATE, N.SPHERICAL_MERCATOR_X, N.SPHERICAL_MERCATOR_Y,
                                      activity_journal=ajournal, with_timespan=True, check=False)
            start, finish = ajournal.start - dt.timedelta(hours=1), ajournal.finish + dt.timedelta(hours=1)
            sdf = statistics(s, N.FATIGUE_D_ANY, N.FITNESS_D_ANY, start=start, finish=finish,
                             owner=self.owner_in, check=False)
            prev = s.query(ActivityJournal). \
                filter(ActivityJournal.start < ajournal.start). \
                order_by(desc(ActivityJournal.start)). \
                first()
            delta = (ajournal.start - prev.start).total_seconds() if prev else None
            return adf, sdf, delta
        except Exception as e:
            log.warning(f'Failed to generate statistics for activity: {e}')
            raise

    def _calculate_stats(self, s, ajournal, data):
        adf, sdf, delta = data
        stats, climbs = {}, None
        stats.update(copy_times(ajournal))
        stats.update(active_stats(adf))
        stats.update(self.__average_power(s, ajournal, stats[N.ACTIVE_TIME]))
        stats.update(times_for_distance(adf))
        stats.update(hrz_stats(adf))
        stats.update(max_med_stats(adf))
        stats.update(max_mean_stats(adf))
        stats.update(direction_stats(adf))
        stats.update(response_stats(sdf, delta))
        if present(adf, N.ELEVATION):
            params = Climb(**loads(Constant.get(s, self.climb_ref).at(s).value))
            climbs = list(find_climbs(adf, params=params))
            add_climb_stats(adf, climbs)
        return data, stats, climbs

    def __average_power(self, s, ajournal, active_time):
        # this doesn't fit nicely anywhere...
        energy = StatisticJournalFloat.at(s, ajournal.start, N.ENERGY_ESTIMATE, PowerCalculator,
                                          ajournal.activity_group)
        if energy and active_time:
            return {N.MEAN_POWER_ESTIMATE: 1000 * energy.value / active_time}
        else:
            return {N.MEAN_POWER_ESTIMATE: 0}

    def _copy_results(self, s, ajournal, loader, data):
        all = ActivityGroup.from_name(s, ActivityGroup.ALL)
        df, stats, climbs = data
        self.__copy(ajournal, loader, stats, T.START, None,
                    None, ajournal.start, type=StatisticJournalTimestamp, extra_group=all)
        self.__copy(ajournal, loader, stats, T.FINISH, None,
                    None, ajournal.start, type=StatisticJournalTimestamp, extra_group=all)
        self.__copy(ajournal, loader, stats, T.TIME, Units.S,
                    S.join(S.MAX, S.SUM, S.MSR), ajournal.start, extra_group=all)
        self.__copy(ajournal, loader, stats, T.ACTIVE_DISTANCE, Units.KM,
                    S.join(S.MAX, S.CNT, S.SUM, S.MSR), ajournal.start, extra_group=all)
        self.__copy(ajournal, loader, stats, T.ACTIVE_TIME, Units.S,
                    S.join(S.MAX, S.SUM, S.MSR), ajournal.start, extra_group=all)
        self.__copy(ajournal, loader, stats, T.ACTIVE_SPEED, Units.KMH,
                    S.join(S.MAX, S.AVG, S.MSR), ajournal.start)
        self.__copy(ajournal, loader, stats, T.MEAN_POWER_ESTIMATE,Units. W,
                    S.join(S.MAX, S.AVG, S.MSR), ajournal.start)
        self.__copy(ajournal, loader, stats, T.DIRECTION, Units.DEG,
                    None, ajournal.start)
        self.__copy(ajournal, loader, stats, T.ASPECT_RATIO, None,
                    None, ajournal.start)
        self.__copy_all(ajournal, loader, stats, T.MIN_KM_TIME_ANY, Units.S,
                        S.join(S.MIN, S.MSR), ajournal.start)
        self.__copy_all(ajournal, loader, stats, T.MED_KM_TIME_ANY, Units.S,
                        S.join(S.MIN, S.MSR), ajournal.start)
        self.__copy_all(ajournal, loader, stats, T.PERCENT_IN_Z_ANY, Units.PC,
                        None, ajournal.start)
        self.__copy_all(ajournal, loader, stats, T.TIME_IN_Z_ANY, Units.S,
                        None, ajournal.start)
        self.__copy_all(ajournal, loader, stats, T.MAX_MED_HR_M_ANY, Units.BPM,
                        S.join(S.MAX, S.MSR), ajournal.start)
        self.__copy_all(ajournal, loader, stats, T.MAX_MEAN_PE_M_ANY, Units.W,
                        S.join(S.MAX, S.MSR), ajournal.start)
        self.__copy_all(ajournal, loader, stats, T._delta(T.FATIGUE_D_ANY), Units.FF,
                        S.join(S.MAX, S.MSR), ajournal.start, extra_group=all)
        self.__copy_all(ajournal, loader, stats, T._delta(T.FITNESS_D_ANY), Units.FF,
                        S.join(S.MAX, S.MSR), ajournal.start, extra_group=all)
        self.__copy_all(ajournal, loader, stats, T.EARNED_D_ANY, Units.S,
                        S.join(S.MAX, S.MSR), ajournal.start, extra_group=all)
        self.__copy_all(ajournal, loader, stats, T.RECOVERY_D_ANY, Units.S,
                        S.join(S.MAX, S.MSR), ajournal.start, extra_group=all)
        self.__copy_all(ajournal, loader, stats, T.PLATEAU_D_ANY, Units.FF,
                        None, ajournal.start, extra_group=all)
        if climbs:
            loader.add(T.TOTAL_CLIMB, Units.M, S.join(S.MAX, S.MSR), ajournal.activity_group, ajournal,
                       sum(climb[N.CLIMB_ELEVATION] for climb in climbs), ajournal.start, StatisticJournalFloat,
                       description=DESCRIPTIONS[T.TOTAL_CLIMB])
            for climb in sorted(climbs, key=lambda climb: climb[N.TIME]):
                self.__copy(ajournal, loader, climb, T.CLIMB_ELEVATION, Units.M,
                            S.join(S.MAX, S.SUM, S.MSR), climb[N.TIME])
                self.__copy(ajournal, loader, climb, T.CLIMB_DISTANCE, Units.KM,
                            S.join(S.MAX, S.SUM, S.MSR), climb[N.TIME])
                self.__copy(ajournal, loader, climb, T.CLIMB_TIME, Units.S,
                            S.join(S.MAX, S.SUM, S.MSR), climb[N.TIME])
                self.__copy(ajournal, loader, climb, T.CLIMB_GRADIENT, Units.PC,
                            S.join(S.MAX, S.MSR), climb[N.TIME])
                self.__copy(ajournal, loader, climb, T.CLIMB_POWER,Units. W,
                            S.join(S.MAX, S.MSR), climb[N.TIME])
                if T.CLIMB_CATEGORY in climb:
                    self.__copy(ajournal, loader, climb, T.CLIMB_CATEGORY, None,
                                None, climb[T.TIME], type=StatisticJournalText)
        if stats:
            log.warning(f'Unsaved statistics: {list(stats.keys())}')

    def __copy_all(self, ajournal, loader, stats, pattern, units, summary, time, type=StatisticJournalFloat,
                   extra_group=None):
        description = DESCRIPTIONS[pattern]
        for title in list(titles_for_names(pattern, stats)):  # list to avoid reading after modification
            self.__copy(ajournal, loader, stats, title, units, summary, time, type=type,
                        extra_group=extra_group, description=description)

    def __copy(self, ajournal, loader, stats, title, units, summary, time, type=StatisticJournalFloat,
               extra_group=None, description=None):
        if not description: description = DESCRIPTIONS[title]
        name = simple_name(title)
        if name in stats:
            groups = [ajournal.activity_group]
            if extra_group: groups += [extra_group]
            for group in groups:
                try:
                    loader.add(title, units, summary, group, ajournal, stats[name], time, type,
                               description=description)
                except:
                    log.warning(f'Failed to load {title}')
                    log_current_exception(traceback=False)
            del stats[name]
        else:
            log.warning(f'Did not calculate {title} '
                        f'({time_to_local_time(ajournal.start)} / {ajournal.activity_group.name})')


DESCRIPTIONS = defaultdict(lambda: None, {
    T.START: '''The start time for the activity.''',
    T.FINISH: '''The finish time for the activity.''',
    T.TIME: '''The total duration of the activity.''',
    T.ACTIVE_DISTANCE: '''The total distance travelled while active (ie not paused).''',
    T.ACTIVE_TIME: '''The total time while active (ie not paused).''',
    T.ACTIVE_SPEED: '''The average speed while active (ie not paused).''',
    T.MEAN_POWER_ESTIMATE: '''The average estimated power.''',
    T.DIRECTION: '''The angular direction (clockwise from North) of the mid-point of teh activity relative to the start.''',
    T.ASPECT_RATIO: f'''The relative extent of the activity along and across the {T.DIRECTION}.''',
    T.MIN_KM_TIME_ANY: '''The shortest time required to cover the given distance.''',
    T.MED_KM_TIME_ANY: '''The median (typical) time required to cover the given distance.''',
    T.PERCENT_IN_Z_ANY: '''The percentage of time in the given HR zone.''',
    T.TIME_IN_Z_ANY: '''The total time in the given HR zone.''',
    T.MAX_MED_HR_M_ANY: '''The highest median HR in the given interval.''',
    T.MAX_MEAN_PE_M_ANY: '''The highest average power estimate in the given interval.''',
    T._delta(T.FATIGUE_D_ANY): '''The change (over the activity) in the SHRIMP Fatigue parameter.''',
    T._delta(T.FITNESS_D_ANY): '''The change (over the activity) in the SHRIMP Fitness parameter.''',
    T.EARNED_D_ANY: '''The time before Fitness returns to the value before the activity.''',
    T.RECOVERY_D_ANY: '''The time before Fatigue returns to the value before the activity.''',
    T.PLATEAU_D_ANY: '''The maximum Fitness achieved if this activity was repeated (with the same time gap to the previous).''',
    T.TOTAL_CLIMB: '''The total height climbed in the detected climbs (only).''',
    T.CLIMB_ELEVATION: '''The difference in elevation between start and end of the climb.''',
    T.CLIMB_DISTANCE: '''The distance travelled during the climb''',
    T.CLIMB_TIME: '''The time spent on the climb.''',
    T.CLIMB_GRADIENT: '''The average inclination of the climb (elevation / distance).''',
    T.CLIMB_POWER: '''The average estimated power during the climb.''',
    T.CLIMB_CATEGORY: '''The climb category (text, "4" to "1" and "HC").'''
})