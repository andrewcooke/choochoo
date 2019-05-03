
from logging import getLogger

from . import ActivityJournalCalculatorMixin, DataFrameCalculatorMixin, MultiProcCalculator
from ..names import RAW_ELEVATION, ELEVATION, DISTANCE, M
from ...data.elevation import fix_elevation
from ...data.frame import activity_statistics, present
from ...squeal import StatisticJournalFloat

log = getLogger(__name__)


class ElevationCalculator(ActivityJournalCalculatorMixin, DataFrameCalculatorMixin, MultiProcCalculator):

    def __init__(self, *args, smooth=3, **kargs):
        self.smooth = smooth
        super().__init__(*args, **kargs)

    def _read_dataframe(self, s, ajournal):
        try:
            df = activity_statistics(s, DISTANCE, RAW_ELEVATION, ELEVATION,
                                     activity_journal=ajournal, with_timespan=True)
            return df
        except Exception as e:
            log.warning(f'Failed to generate statistics for elevation: {e}')
            raise

    def _calculate_stats(self, s, ajournal, df):
        return fix_elevation(df, smooth=self.smooth)

    def _copy_results(self, s, ajournal, loader, df):
        for time, row in df.iterrows():
            loader.add(ELEVATION, M, None, ajournal.activity_group, ajournal, row[ELEVATION], time,
                       StatisticJournalFloat)
