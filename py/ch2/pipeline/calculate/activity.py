
import datetime as dt
from json import loads
from logging import getLogger

from sqlalchemy import desc

from .response import ResponseCalculator
from .elevation import ElevationCalculator
from .impulse import ImpulseCalculator
from .power import PowerCalculator
from .utils import ProcessCalculator, ActivityJournalCalculatorMixin, DataFrameCalculatorMixin
from ..pipeline import OwnerInMixin, LoaderMixin
from ..read.segment import SegmentReader
from ...data import Statistics
from ...data.activity import active_stats, times_for_distance, hrz_stats, max_med_stats, max_mean_stats, \
    direction_stats, copy_times, round_km, MAX_MINUTES
from ...data.climb import find_climbs, Climb, add_climb_stats
from ...data.frame import present
from ...data.response import response_stats, DIGITS
from ...lib.data import safe_dict
from ...names import N, T, S, U, SPACE
from ...sql import Constant, ActivityJournal, StatisticJournal, StatisticJournalType, StatisticName

log = getLogger(__name__)


class ActivityCalculator(LoaderMixin, OwnerInMixin,
                         ActivityJournalCalculatorMixin, DataFrameCalculatorMixin, ProcessCalculator):

    def __init__(self, *args, climb=None, response_prefix=None, **kargs):
        self.climb_ref = climb
        self.response_prefix = response_prefix
        super().__init__(*args, add_serial=False, **kargs)

    def _startup(self, s):
        super()._startup(s)
        self._provides(s, T.START, StatisticJournalType.TIMESTAMP, None, None,
                       'The start time for the activity.')
        self._provides(s, T.FINISH, StatisticJournalType.TIMESTAMP, None, None,
                       'The finish time for the activity.')
        self._provides(s, T.TIME, StatisticJournalType.FLOAT, U.S, S.join(S.MAX, S.SUM, S.MSR),
                       'The total duration of the activity.')
        self._provides(s, T.ACTIVE_DISTANCE, StatisticJournalType.FLOAT, U.KM, S.join(S.MAX, S.CNT, S.SUM, S.MSR),
                       'The total distance travelled while active (ie not paused).')
        self._provides(s, T.ACTIVE_TIME, StatisticJournalType.FLOAT, U.S, S.join(S.MAX, S.SUM, S.MSR),
                       'The total time while active (ie not paused).')
        self._provides(s, T.ACTIVE_SPEED, StatisticJournalType.FLOAT, U.KMH, S.join(S.MAX, S.AVG, S.MSR),
                       'The average speed while active (ie not paused).')
        self._provides(s, T.MEAN_POWER_ESTIMATE, StatisticJournalType.FLOAT, U.W, S.join(S.MAX, S.AVG, S.MSR),
                       'The average estimated power.')
        self._provides(s, T.DIRECTION, StatisticJournalType.FLOAT, U.DEG, None,
                       'The angular direction (clockwise from North) of the mid-point of the activity relative to the start.')
        self._provides(s, T.ASPECT_RATIO, StatisticJournalType.FLOAT, None, None,
                       'The relative extent of the activity along and across the {T.DIRECTION}.')
        self._provides(s, T.MIN_KM_TIME, StatisticJournalType.FLOAT, U.S, S.join(S.MIN, S.MSR),
                       'The shortest time required to cover the given distance.', values=round_km())
        self._provides(s, T.MED_KM_TIME, StatisticJournalType.FLOAT, U.S, S.join(S.MIN, S.MSR),
                       'The median (typical) time required to cover the given distance.', values=round_km())
        self._provides(s, T.PERCENT_IN_Z, StatisticJournalType.FLOAT, U.PC, None,
                       'The percentage of time in the given HR zone.', values=range(1, 7))
        self._provides(s, T.TIME_IN_Z, StatisticJournalType.FLOAT, U.S, None,
                       'The total time in the given HR zone.', values=range(1, 7))
        self._provides(s, T.MAX_MED_HR_M, StatisticJournalType.FLOAT, U.BPM, S.join(S.MAX, S.MSR),
                       'The highest median HR in the given interval.', values=MAX_MINUTES)
        self._provides(s, T.MAX_MEAN_PE_M, StatisticJournalType.FLOAT, U.W, S.join(S.MAX, S.MSR),
                       'The highest average power estimate in the given interval.', values=MAX_MINUTES)
        self._provides(s, T.TOTAL_CLIMB, StatisticJournalType.FLOAT, U.M, S.join(S.MAX, S.MSR),
                       'The total height climbed in the detected climbs (only).')
        self._provides(s, T.CLIMB_ELEVATION, StatisticJournalType.FLOAT, U.M, S.join(S.MAX, S.SUM, S.MSR),
                       'The difference in elevation between start and end of the climb.')
        self._provides(s, T.CLIMB_DISTANCE, StatisticJournalType.FLOAT, U.KM, S.join(S.MAX, S.SUM, S.MSR),
                       'The distance travelled during the climb.')
        self._provides(s, T.CLIMB_TIME, StatisticJournalType.FLOAT, U.S, S.join(S.MAX, S.SUM, S.MSR),
                       'The time spent on the climb.')
        self._provides(s, T.CLIMB_GRADIENT, StatisticJournalType.FLOAT, U.PC,  S.join(S.MAX, S.MSR),
                       'The average inclination of the climb (elevation / distance).')
        self._provides(s, T.CLIMB_POWER, StatisticJournalType.FLOAT, U.W,  S.join(S.MAX, S.MSR),
                       'The average estimated power during the climb.')
        self._provides(s, T.CLIMB_CATEGORY, StatisticJournalType.TEXT, None, None,
                       'The climb category (text, "4" to "1" and "HC").')
        # these are complicated :( because exact names are calculated elsewhere
        for statistic_name in s.query(StatisticName). \
                filter(StatisticName.name.like('%' + N.FITNESS_ANY),
                       StatisticName.owner == ResponseCalculator).all():
            self._provides(s, T._delta(statistic_name.title), StatisticJournalType.FLOAT, U.FF, S.join(S.MAX, S.MSR),
                           'The change (over the activity) in the SHRIMP Fitness parameter.')
            days = int(DIGITS.search(statistic_name.name).group(1))
            # there may be a bug here with the name prefix not being propagated
            self._provides(s, T.EARNED_D % days, StatisticJournalType.FLOAT, U.S, S.join(S.MAX, S.MSR),
                           'The time before Fitness returns to the value before the activity.')
            self._provides(s, T.PLATEAU_D % days, StatisticJournalType.FLOAT, U.S, S.join(S.MAX, S.MSR),
                           'The maximum Fitness achieved if this activity was repeated (with the same time gap to the previous).')
        for statistic_name in s.query(StatisticName). \
                filter(StatisticName.name.like('%' + N.FATIGUE_ANY),
                       StatisticName.owner == ResponseCalculator).all():
            self._provides(s, T._delta(statistic_name.title), StatisticJournalType.FLOAT, U.FF, S.join(S.MAX, S.MSR),
                           'The change (over the activity) in the SHRIMP Fatigue parameter.')
            days = int(DIGITS.search(statistic_name.name).group(1))
            # there may be a bug here with the name prefix not being propagated
            self._provides(s, T.RECOVERY_D % days, StatisticJournalType.FLOAT, U.S, S.join(S.MAX, S.MSR),
                           'The time before Fatigue returns to the value before the activity.')

    def _read_dataframe(self, s, ajournal):
        try:
            adf = Statistics(s, activity_journal=ajournal, with_timespan=True). \
                by_name(SegmentReader, N.DISTANCE, N.HEART_RATE, N.SPHERICAL_MERCATOR_X, N.SPHERICAL_MERCATOR_Y). \
                by_name(ElevationCalculator, N.ELEVATION). \
                by_name(ImpulseCalculator, N.HR_ZONE). \
                by_name(PowerCalculator, N.POWER_ESTIMATE).df
            if self.response_prefix:
                start, finish = ajournal.start - dt.timedelta(hours=1), ajournal.finish + dt.timedelta(hours=1)
                fitness = self.response_prefix + SPACE + N.FITNESS_ANY
                fatigue = self.response_prefix + SPACE + N.FATIGUE_ANY
                sdf = Statistics(s, start=start, finish=finish). \
                    by_name(self.owner_in, fitness, fatigue, like=True).with_. \
                    drop_prefix(self.response_prefix).df
            else:
                sdf = None
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
        if sdf is not None:
            stats.update(response_stats(sdf, delta))
        if present(adf, N.ELEVATION):
            params = Climb(**loads(Constant.from_name(s, self.climb_ref).at(s).value))
            climbs = list(find_climbs(adf, params=params))
            add_climb_stats(adf, climbs)
        return data, stats, climbs

    @safe_dict
    def __average_power(self, s, ajournal, active_time):
        # this doesn't fit nicely anywhere...
        energy = StatisticJournal.at(s, ajournal.start, N.ENERGY_ESTIMATE, PowerCalculator,
                                     ajournal.activity_group)
        if energy and active_time:
            return {N.MEAN_POWER_ESTIMATE: 1000 * energy.value / active_time}
        else:
            return {N.MEAN_POWER_ESTIMATE: 0}

    def _copy_results(self, s, ajournal, loader, data):
        df, stats, climbs = data
        if climbs:
            stats[N.TOTAL_CLIMB] = sum(climb[N.CLIMB_ELEVATION] for climb in climbs)
            for climb in sorted(climbs, key=lambda climb: climb[N.TIME]):
                time = climb.pop(N.TIME)
                for name in climb.keys():
                    loader.add_data(name, ajournal, climb[name], time)
        for name in stats.keys():
            loader.add_data(name, ajournal, stats[name], ajournal.start)
