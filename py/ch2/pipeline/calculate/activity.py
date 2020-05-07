
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
from ...names import Names, Titles, Summaries as S, Units, _delta, summaries, like
from ...data.response import response_stats
from ...lib import time_to_local_time
from ...lib.log import log_current_exception
from ...sql import StatisticJournalFloat, Constant, StatisticJournalText, ActivityGroup, StatisticJournalTimestamp, \
    ActivityJournal

log = getLogger(__name__)


class ActivityCalculator(ActivityJournalCalculatorMixin, DataFrameCalculatorMixin, MultiProcCalculator):

    def __init__(self, *args, climb=None, **kargs):
        self.climb_ref = climb
        super().__init__(*args, **kargs)

    def _read_dataframe(self, s, ajournal):
        try:
            adf = activity_statistics(s, Names.DISTANCE, Names.ELEVATION, Names.HEART_RATE, Names.HR_ZONE, 
                                      Names.POWER_ESTIMATE, Names.SPHERICAL_MERCATOR_X, Names.SPHERICAL_MERCATOR_Y,
                                      activity_journal=ajournal, with_timespan=True, check=False)
            start, finish = ajournal.start - dt.timedelta(hours=1), ajournal.finish + dt.timedelta(hours=1)
            sdf = statistics(s, Names.FATIGUE_D_ANY, Names.FITNESS_D_ANY, start=start, finish=finish,
                             owner=self.owner_in, check=False)
            prev = s.query(ActivityJournal). \
                filter(ActivityJournal.start < ajournal.start). \
                order_by(desc(ActivityJournal.start)). \
                limit(1).one_or_none()
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
        stats.update(self.__average_power(s, ajournal, stats[Names.ACTIVE_TIME]))
        stats.update(times_for_distance(adf))
        stats.update(hrz_stats(adf))
        stats.update(max_med_stats(adf))
        stats.update(max_mean_stats(adf))
        stats.update(direction_stats(adf))
        stats.update(response_stats(sdf, delta))
        if present(adf, Names.ELEVATION):
            params = Climb(**loads(Constant.get(s, self.climb_ref).at(s).value))
            climbs = list(find_climbs(adf, params=params))
            add_climb_stats(adf, climbs)
        return data, stats, climbs

    def __average_power(self, s, ajournal, active_time):
        # this doesn't fit nicely anywhere...
        energy = StatisticJournalFloat.at(s, ajournal.start, Names.ENERGY_ESTIMATE, PowerCalculator,
                                          ajournal.activity_group)
        if energy and active_time:
            return {Titles.MEAN_POWER_ESTIMATE: 1000 * energy.value / active_time}
        else:
            return {Titles.MEAN_POWER_ESTIMATE: 0}

    def _copy_results(self, s, ajournal, loader, data):
        all = ActivityGroup.from_name(s, ActivityGroup.ALL)
        df, stats, climbs = data
        self.__copy(ajournal, loader, stats, Titles.START, None,
                    None, ajournal.start, type=StatisticJournalTimestamp, extra_group=all)
        self.__copy(ajournal, loader, stats, Titles.FINISH, None,
                    None, ajournal.start, type=StatisticJournalTimestamp, extra_group=all)
        self.__copy(ajournal, loader, stats, Titles.TIME, Units.S,
                    summaries(S.MAX, S.SUM, S.MSR), ajournal.start, extra_group=all)
        self.__copy(ajournal, loader, stats, Titles.ACTIVE_DISTANCE, Units.KM,
                    summaries(S.MAX, S.CNT, S.SUM, S.MSR), ajournal.start, extra_group=all)
        self.__copy(ajournal, loader, stats, Titles.ACTIVE_TIME, Units.S,
                    summaries(S.MAX, S.SUM, S.MSR), ajournal.start, extra_group=all)
        self.__copy(ajournal, loader, stats, Titles.ACTIVE_SPEED, Units.KMH,
                    summaries(S.MAX, S.AVG, S.MSR), ajournal.start)
        self.__copy(ajournal, loader, stats, Titles.MEAN_POWER_ESTIMATE,Units. W,
                    summaries(S.MAX, S.AVG, S.MSR), ajournal.start)
        self.__copy(ajournal, loader, stats, Titles.DIRECTION, Units.DEG,
                    None, ajournal.start)
        self.__copy(ajournal, loader, stats, Titles.ASPECT_RATIO, None,
                    None, ajournal.start)
        self.__copy_all(ajournal, loader, stats, Titles.MIN_KM_TIME_ANY, Units.S,
                        summaries(S.MIN, S.MSR), ajournal.start)
        self.__copy_all(ajournal, loader, stats, Titles.MED_KM_TIME_ANY, Units.S,
                        summaries(S.MIN, S.MSR), ajournal.start)
        self.__copy_all(ajournal, loader, stats, Titles.PERCENT_IN_Z_ANY, Units.PC,
                        None, ajournal.start)
        self.__copy_all(ajournal, loader, stats, Titles.TIME_IN_Z_ANY, Units.S,
                        None, ajournal.start)
        self.__copy_all(ajournal, loader, stats, Titles.MAX_MED_HR_M_ANY, Units.BPM,
                        summaries(S.MAX, S.MSR), ajournal.start)
        self.__copy_all(ajournal, loader, stats, Titles.MAX_MEAN_PE_M_ANY, Units.W,
                        summaries(S.MAX, S.MSR), ajournal.start)
        self.__copy_all(ajournal, loader, stats, _delta(Titles.FATIGUE_D_ANY), Units.FF,
                        summaries(S.MAX, S.MSR), ajournal.start, extra_group=all)
        self.__copy_all(ajournal, loader, stats, _delta(Titles.FITNESS_D_ANY), Units.FF,
                        summaries(S.MAX, S.MSR), ajournal.start, extra_group=all)
        self.__copy_all(ajournal, loader, stats, Titles.EARNED_D_ANY, Units.S,
                        summaries(S.MAX, S.MSR), ajournal.start, extra_group=all)
        self.__copy_all(ajournal, loader, stats, Titles.RECOVERY_D_ANY, Units.S,
                        summaries(S.MAX, S.MSR), ajournal.start, extra_group=all)
        self.__copy_all(ajournal, loader, stats, Titles.PLATEAU_D_ANY, Units.FF,
                        None, ajournal.start, extra_group=all)
        if climbs:
            loader.add(Titles.TOTAL_CLIMB, Units.M, summaries(S.MAX, S.MSR), ajournal.activity_group, ajournal,
                       sum(climb[Names.CLIMB_ELEVATION] for climb in climbs), ajournal.start, StatisticJournalFloat,
                       description=DESCRIPTIONS[Titles.TOTAL_CLIMB])
            for climb in sorted(climbs, key=lambda climb: climb[Titles.TIME]):
                self.__copy(ajournal, loader, climb, Titles.CLIMB_ELEVATION, Units.M,
                            summaries(S.MAX, S.SUM, S.MSR), climb[Titles.TIME])
                self.__copy(ajournal, loader, climb, Titles.CLIMB_DISTANCE, Units.KM,
                            summaries(S.MAX, S.SUM, S.MSR), climb[Titles.TIME])
                self.__copy(ajournal, loader, climb, Titles.CLIMB_TIME, Units.S,
                            summaries(S.MAX, S.SUM, S.MSR), climb[Titles.TIME])
                self.__copy(ajournal, loader, climb, Titles.CLIMB_GRADIENT, Units.PC,
                            summaries(S.MAX, S.MSR), climb[Titles.TIME])
                self.__copy(ajournal, loader, climb, Titles.CLIMB_POWER,Units. W,
                            summaries(S.MAX, S.MSR), climb[Titles.TIME])
                if Titles.CLIMB_CATEGORY in climb:
                    self.__copy(ajournal, loader, climb, Titles.CLIMB_CATEGORY, None,
                                None, climb[Titles.TIME], type=StatisticJournalText)
        if stats:
            log.warning(f'Unsaved statistics: {list(stats.keys())}')

    def __copy_all(self, ajournal, loader, stats, pattern, units, summary, time, type=StatisticJournalFloat,
                   extra_group=None):
        description = DESCRIPTIONS[pattern]
        for name in like(pattern, stats):
            self.__copy(ajournal, loader, stats, name, units, summary, time, type=type,
                        extra_group=extra_group, description=description)

    def __copy(self, ajournal, loader, stats, name, units, summary, time, type=StatisticJournalFloat,
               extra_group=None, description=None):
        if name in stats:
            if not description: description = DESCRIPTIONS[name]
            groups = [ajournal.activity_group]
            if extra_group: groups += [extra_group]
            for group in groups:
                try:
                    loader.add(name, units, summary, group, ajournal, stats[name], time, type,
                               description=description)
                except:
                    log.warning(f'Failed to load {name}')
                    log_current_exception(traceback=False)
            del stats[name]
        else:
            log.warning(f'Did not calculate {name} '
                        f'({time_to_local_time(ajournal.start)} / {ajournal.activity_group.name}')


DESCRIPTIONS = defaultdict(lambda: None, {
    Titles.START: '''The start time for the activity.''',
    Titles.FINISH: '''The finish time for the activity.''',
    Titles.TIME: '''The total duration of the activity.''',
    Titles.ACTIVE_DISTANCE: '''The total distance travelled while active (ie not paused).''',
    Titles.ACTIVE_TIME: '''The total time while active (ie not paused).''',
    Titles.ACTIVE_SPEED: '''The average speed while active (ie not paused).''',
    Titles.MEAN_POWER_ESTIMATE: '''The average estimated power.''',
    Titles.DIRECTION: '''The angular direction (clockwise from North) of the mid-point of teh activity relative to the start.''',
    Titles.ASPECT_RATIO: f'''The relative extent of the activity along and across the {Titles.DIRECTION}.''',
    Titles.MIN_KM_TIME_ANY: '''The shortest time required to cover the given distance.''',
    Titles.MED_KM_TIME_ANY: '''The median(typical) time required to cover the given distance.''',
    Titles.PERCENT_IN_Z_ANY: '''The percentage of time in the given HR zone.''',
    Titles.TIME_IN_Z_ANY: '''The total time in the given HR zone.''',
    Titles.MAX_MED_HR_M_ANY: '''The highest median HR in the given interval.''',
    Titles.MAX_MEAN_PE_M_ANY: '''The highest average power estimate in the given interval.''',
    _delta(Titles.FATIGUE_D_ANY): '''The change (over the activity) in the SHRIMP Fatigue parameter.''',
    _delta(Titles.FITNESS_D_ANY): '''The change (over the activity) in the SHRIMP Fitness parameter.''',
    Titles.EARNED_D_ANY: '''The time before Fitness returns to the value before the activity.''',
    Titles.RECOVERY_D_ANY: '''The time before Fatigue returns to the value before the activity.''',
    Titles.PLATEAU_D_ANY: '''The maximum Fitness achieved if this activity was repeated (with the same time gap to the previous).''',
    Titles.TOTAL_CLIMB: '''The total height climbed in the detected climbs (only).''',
    Titles.CLIMB_ELEVATION: '''The difference in elevation between start and end of the climb.''',
    Titles.CLIMB_DISTANCE: '''The distance travelled during the climb''',
    Titles.CLIMB_TIME: '''The time spent on the climb.''',
    Titles.CLIMB_GRADIENT: '''The average inclination of the climb (elevation / distance).''',
    Titles.CLIMB_POWER: '''The average estimated power during the climb.''',
    Titles.CLIMB_CATEGORY: '''The climb category (text, "4" to "1" and "HC").'''
})