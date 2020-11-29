
from collections import namedtuple
from json import loads
from logging import getLogger

from .utils import ProcessCalculator, ActivityGroupProcessCalculator, DataFrameCalculatorMixin
from ..pipeline import OwnerInMixin, LoaderMixin
from ...common.math import is_nan
from ...data import Statistics
from ...data.impulse import hr_zone, impulse_10
from ...names import N, T, SPACE
from ...sql import Constant, StatisticJournalType

log = getLogger(__name__)

# constraint comes from constant
HRImpulse = namedtuple('HRImpulse', 'title, gamma, zero, one, max_secs')


class ImpulseCalculator(LoaderMixin, OwnerInMixin, DataFrameCalculatorMixin,
                        ActivityGroupProcessCalculator):

    def __init__(self, *args, prefix=None, impulse_constant=None, activity_group=None, **kargs):
        self.impulse_constant_ref = self._assert('impulse_constant', impulse_constant)
        self.prefix = self._assert('prefix', prefix)
        super().__init__(*args, activity_group=activity_group, **kargs)

    def _startup(self, s):
        super()._startup(s)
        self.impulse_constant = Constant.from_name(s, self.impulse_constant_ref)
        self.impulse = HRImpulse(**loads(self.impulse_constant.at(s).value))
        log.debug('%s: %s' % (self.impulse_constant, self.impulse))
        self._provides(s, T.HR_ZONE, StatisticJournalType.FLOAT, None, None,
                       'The SHRIMP HR zone.')
        name_group = self.prefix + SPACE + self.impulse_constant.short_name
        self._provides(s, name_group, StatisticJournalType.FLOAT, None, None,
                       'The SHRIMP HR impulse over 10 seconds.', title=self.impulse.title)

    def _read_dataframe(self, s, ajournal):
        try:
            heart_rate_df = Statistics(s, activity_journal=ajournal). \
                by_name(self.owner_in, N.HEART_RATE).df
            fthr_df = Statistics(s).by_name(Constant, N.FTHR).df
        except Exception as e:
            log.warning(f'Failed to generate statistics for activity: {e}')
            raise
        if fthr_df.empty:
            raise Exception(f'No {N.FTHR} defined for {ajournal.activity_group}')
        return heart_rate_df, fthr_df

    def _calculate_stats(self, s, ajournal, data):
        heart_rate_df, fthr_df = data
        hr_zone(heart_rate_df, fthr_df)
        impulse_df = impulse_10(heart_rate_df, self.impulse)
        # join so that we can iterate over values in time order
        stats = impulse_df.join(heart_rate_df, how='outer')
        return stats

    def _copy_results(self, s, ajournal, loader, stats):
        name_group = self.prefix + SPACE + self.impulse_constant.short_name  # drop activity group as present elsewhere
        for time, row in stats.iterrows():
            if N.HR_ZONE in row and not is_nan(row[N.HR_ZONE]):
                loader.add_data(N.HR_ZONE, ajournal, row[N.HR_ZONE], time)
            if N.HR_IMPULSE_10 in row and not is_nan(row[N.HR_IMPULSE_10]):
                loader.add_data(name_group, ajournal, row[N.HR_IMPULSE_10], time)
        # if there are no values, add a single 1 so we don't re-process
        if not loader:
            loader.add_data(N.HR_ZONE, ajournal, 1, ajournal.start)
