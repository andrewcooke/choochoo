
from collections import namedtuple
from json import loads
from logging import getLogger

import numpy as np

from .utils import MultiProcCalculator, ActivityGroupCalculatorMixin, DataFrameCalculatorMixin
from ..pipeline import OwnerInMixin
from ...data.frame import activity_statistics, statistics
from ...data.impulse import hr_zone, impulse_10
from ...names import Names, Titles
from ...sql import Constant, StatisticJournalFloat, ActivityGroup

log = getLogger(__name__)

# constraint comes from constant
HRImpulse = namedtuple('HRImpulse', 'title, gamma, zero, one, max_secs')


class ImpulseCalculator(OwnerInMixin, ActivityGroupCalculatorMixin, DataFrameCalculatorMixin, MultiProcCalculator):

    def __init__(self, *args, prefix=None, impulse_constant=None, **kargs):
        self.impulse_constant_name = self._assert('impulse_constant', impulse_constant)
        self.prefix = self._assert('prefix', prefix)
        super().__init__(*args, **kargs)

    def _startup(self, s):
        self.impulse_constant = Constant.get(s, self.impulse_constant_name)
        self.impulse = HRImpulse(**loads(self.impulse_constant.at(s).value))
        self.all = ActivityGroup.from_name(s, ActivityGroup.ALL)
        log.debug('%s: %s' % (self.impulse_constant, self.impulse))

    def _read_dataframe(self, s, ajournal):
        try:
            heart_rate_df = activity_statistics(s, Names.HEART_RATE, activity_journal=ajournal,
                                                owners=(self.owner_in,))
            fthr_df = statistics(s, Names.FTHR, activity_group=ajournal.activity_group)
        except Exception as e:
            log.warning(f'Failed to generate statistics for activity: {e}')
            raise
        if fthr_df.empty:
            raise Exception(f'No {Names.FTHR} defined for {ajournal.activity_group}')
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
        name_group = self.prefix + '_' + self.impulse_constant.short_name  # drop activity group as present elsewhere
        name_all = self.prefix + '_' + Names.HR_IMPULSE_10
        for time, row in stats.iterrows():
            if not np.isnan(row[Names.HR_ZONE]):
                loader.add(Titles.HR_ZONE, None, None, ajournal.activity_group, ajournal, row[Names.HR_ZONE], time,
                           StatisticJournalFloat, description=hr_description)
            if not np.isnan(row[Names.HR_IMPULSE_10]):
                # load a copy to the activity group as well as to all so that we can extract / display
                # easily in, for example, std_activity_statistics
                loader.add(name_group, None, None, ajournal.activity_group, ajournal, row[Names.HR_IMPULSE_10], time,
                           StatisticJournalFloat, description=impulse_description, title=title)
                # copy for global FF statistics
                loader.add(name_all, None, None, self.all, ajournal, row[Names.HR_IMPULSE_10], time,
                           StatisticJournalFloat, description=impulse_description, title=title)
        # if there are no values, add a single null so we don't re-process
        if not loader:
            loader.add(Titles.HR_ZONE, None, None, ajournal.activity_group, ajournal, None, ajournal.start,
                       StatisticJournalFloat, description=hr_description)
