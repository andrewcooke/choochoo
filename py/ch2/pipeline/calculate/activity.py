
import datetime as dt
from collections import namedtuple
from logging import getLogger

from sqlalchemy import desc

from .elevation import ElevationCalculator
from .impulse import ImpulseCalculator
from .power import PowerCalculator
from .response import ResponseCalculator
from .utils import ActivityJournalProcessCalculator, DataFrameCalculatorMixin
from ..pipeline import OwnerInMixin, LoaderMixin
from ..read.activity import ActivityReader
from ...data import Statistics
from ...data.activity import active_stats, times_for_distance, hrz_stats, max_med_stats, max_mean_stats, \
    direction_stats, copy_times, round_km, MAX_MINUTES
from ...data.response import response_stats, DIGITS
from ...lib.data import safe_dict
from ...names import N, T, S, U, SPACE
from ...sql import ActivityJournal, StatisticJournal, StatisticJournalType, StatisticName, Sector
from ...sql.tables.sector import SectorJournal, SectorType

log = getLogger(__name__)


class ActivityCalculator(LoaderMixin, OwnerInMixin, DataFrameCalculatorMixin,
                         ActivityJournalProcessCalculator):

    def __init__(self, *args, response_prefix=None, **kargs):
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
                by_name(ActivityReader, N.DISTANCE, N.HEART_RATE, N.SPHERICAL_MERCATOR_X, N.SPHERICAL_MERCATOR_Y). \
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
            climbs = s.query(SectorJournal). \
                join(Sector). \
                filter(SectorJournal.activity_journal == ajournal,
                       Sector.type == SectorType.CLIMB). \
                all()
            prev = s.query(ActivityJournal). \
                filter(ActivityJournal.start < ajournal.start). \
                order_by(desc(ActivityJournal.start)). \
                first()
            delta = (ajournal.start - prev.start).total_seconds() if prev else None
            return adf, sdf, climbs, delta
        except Exception as e:
            log.warning(f'Failed to generate statistics for activity: {e}')
            raise

    def _calculate_stats(self, s, ajournal, data):
        adf, sdf, climbs, delta = data
        stats = {}
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
        if climbs:
            stats.update({N.TOTAL_CLIMB: self.__total_climbed(climbs)})
        return data, stats

    def __total_climbed(self, climbs):
        DistanceElevation = namedtuple('DistanceElevation', 'distance,elevation')
        merged = [(DistanceElevation(climb.start_distance, climb.start_elevation),
                   DistanceElevation(climb.finish_distance, climb.finish_elevation))
                  for climb in climbs]
        START, FINISH = 0, 1
        merged = sorted(merged, key=lambda pair: pair[START].distance)
        log.debug(f'Merging climbs: {merged}')
        i = 0
        while i < len(merged) - 1:
            left, right = merged[i], merged[i+1]
            if left[FINISH].distance >= right[FINISH].distance:
                del merged[i+1]
            elif left[FINISH].distance >= right[START].distance:
                merged[i] = (left[START], right[FINISH])
                del merged[i+1]
            else:
                i += 1
        log.debug(f'Merged climbs: {merged}')
        total = sum(finish.elevation - start.elevation for start, finish in merged)
        log.debug(f'Total {total} from merged climbs: {merged}')
        return total

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
        df, stats = data
        for name in stats.keys():
            loader.add_data(name, ajournal, stats[name], ajournal.start)
