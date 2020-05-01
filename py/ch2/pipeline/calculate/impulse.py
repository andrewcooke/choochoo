
from collections import namedtuple
from json import loads
from logging import getLogger

import numpy as np

from . import MultiProcCalculator, ActivityGroupCalculatorMixin, DataFrameCalculatorMixin
from ...data.frame import activity_statistics, statistics
from ...data.impulse import hr_zone, impulse_10
from ...names import FTHR, HEART_RATE, HR_ZONE, ALL, HR_IMPULSE_10
from ...sql import Constant, StatisticJournalFloat, ActivityGroup

log = getLogger(__name__)

# constraint comes from constant
HRImpulse = namedtuple('HRImpulse', 'gamma, zero, one, max_secs')


class ImpulseCalculator(ActivityGroupCalculatorMixin, DataFrameCalculatorMixin, MultiProcCalculator):

    def __init__(self, *args, impulse_ref=None, **kargs):
        self.impulse_ref = self._assert('impulse_ref', impulse_ref)
        super().__init__(*args, **kargs)

    def _startup(self, s):
        self.impulse = HRImpulse(**loads(Constant.get(s, self.impulse_ref).at(s).value))
        self.all = ActivityGroup.from_name(s, ALL)
        log.debug('%s: %s' % (self.impulse_ref, self.impulse))

    def _read_dataframe(self, s, ajournal):
        try:
            heart_rate_df = activity_statistics(s, HEART_RATE, activity_journal=ajournal)
            fthr_df = statistics(s, FTHR, activity_group=ajournal.activity_group)
        except Exception as e:
            log.warning(f'Failed to generate statistics for activity: {e}')
            raise
        if fthr_df.empty:
            raise Exception(f'No {FTHR} defined for {ajournal.activity_group}')
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
        impulse_description = 'The SHRIMP HT impulse over 10 seconds.'
        for time, row in stats.iterrows():
            if not np.isnan(row[HR_ZONE]):
                loader.add(HR_ZONE, None, None, ajournal.activity_group, ajournal, row[HR_ZONE], time,
                           StatisticJournalFloat, description=hr_description)
            if not np.isnan(row[HR_IMPULSE_10]):
                # load a copy to the activity group as well as to all so that we can extract / display
                # easily in, for example, std_activity_statistics
                loader.add(HR_IMPULSE_10, None, None, ajournal.activity_group, ajournal,
                           row[HR_IMPULSE_10], time, StatisticJournalFloat, description=impulse_description)
                # copy for global FF statistics
                loader.add(HR_IMPULSE_10, None, None, self.all, ajournal,
                           row[HR_IMPULSE_10], time, StatisticJournalFloat, description=impulse_description)
        # if there are no values, add a single null so we don't re-process
        if not loader:
            loader.add(HR_ZONE, None, None, ajournal.activity_group, ajournal, None, ajournal.start,
                       StatisticJournalFloat, description=hr_description)
