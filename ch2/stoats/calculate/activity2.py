
from logging import getLogger

from . import ActivityJournalCalculatorMixin, DataFrameCalculatorMixin, MultiProcCalculator
from ..names import ELEVATION, DISTANCE, M, POWER_ESTIMATE, HEART_RATE
from ...data.frame import activity_statistics, present
from ...squeal import StatisticJournalFloat

log = getLogger(__name__)


class Activity2Calculator(ActivityJournalCalculatorMixin, DataFrameCalculatorMixin, MultiProcCalculator):

    def __init__(self, *args, cost_calc=2, cost_write=1, **kargs):
        super().__init__(*args, cost_calc=cost_calc, cost_write=cost_write, **kargs)

    def _read_dataframe(self, s, ajournal):
        try:
            df = activity_statistics(s, DISTANCE, ELEVATION, HEART_RATE, POWER_ESTIMATE,
                                     activity_journal=ajournal, with_timespan=True)
            return df
        except Exception as e:
            log.warning(f'Failed to generate statistics for elevation: {e}')
            raise

    def _calculate_stats(self, s, ajournal, df):
        if not present(df, ELEVATION):
            pass
        return df

    def _copy_results(self, s, ajournal, loader, df):
        for time, row in df.iterrows():
            loader.add(ELEVATION, M, None, ajournal.activity_group, ajournal, row[ELEVATION], time,
                       StatisticJournalFloat)
