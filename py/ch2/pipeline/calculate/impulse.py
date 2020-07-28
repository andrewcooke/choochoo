
from collections import namedtuple
from json import loads
from logging import getLogger

import numpy as np

from .utils import ProcessCalculator, ActivityGroupCalculatorMixin, DataFrameCalculatorMixin
from ..pipeline import OwnerInMixin, LoaderMixin
from ...data import Statistics
from ...data.frame import valid
from ...data.impulse import hr_zone, impulse_10
from ...names import N, Titles, SPACE
from ...sql import Constant, StatisticJournalFloat

log = getLogger(__name__)

# constraint comes from constant
HRImpulse = namedtuple('HRImpulse', 'title, gamma, zero, one, max_secs')


class ImpulseCalculator(LoaderMixin, OwnerInMixin,
                        ActivityGroupCalculatorMixin, DataFrameCalculatorMixin, ProcessCalculator):

    def __init__(self, *args, prefix=None, impulse_constant=None, activity_group=None, **kargs):
        self.impulse_constant_ref = self._assert('impulse_constant', impulse_constant)
        self.prefix = self._assert('prefix', prefix)
        super().__init__(*args, timestamp_constraint=activity_group, activity_group=activity_group, **kargs)

    def _startup(self, s):
        super()._startup(s)
        self.impulse_constant = Constant.from_name(s, self.impulse_constant_ref)
        self.impulse = HRImpulse(**loads(self.impulse_constant.at(s).value))
        log.debug('%s: %s' % (self.impulse_constant, self.impulse))

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
        hr_description = 'The SHRIMP HR zone.'
        impulse_description = 'The SHRIMP HR impulse over 10 seconds.'
        title = self.impulse.title
        name_group = self.prefix + SPACE + self.impulse_constant.short_name  # drop activity group as present elsewhere
        for time, row in stats.iterrows():
            if N.HR_ZONE in row and valid(row[N.HR_ZONE]):
                loader.add(Titles.HR_ZONE, None, None, ajournal, row[N.HR_ZONE], time,
                           StatisticJournalFloat, description=hr_description)
            if N.HR_IMPULSE_10 in row and valid(row[N.HR_IMPULSE_10]):
                loader.add(name_group, None, None, ajournal, row[N.HR_IMPULSE_10], time,
                           StatisticJournalFloat, description=impulse_description, title=title)
        # if there are no values, add a single 1 so we don't re-process
        if not loader:
            loader.add(Titles.HR_ZONE, None, None, ajournal, 1, ajournal.start,
                       StatisticJournalFloat, description=hr_description)
