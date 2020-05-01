
from logging import getLogger

from . import MultiProcCalculator, ActivityJournalCalculatorMixin, DataFrameCalculatorMixin
from ...data.elevation import smooth_elevation
from ...data.frame import activity_statistics, present
from ...names import RAW_ELEVATION, ELEVATION, DISTANCE, M, GRADE, PC, ALTITUDE
from ...sql import StatisticJournalFloat

log = getLogger(__name__)


class ElevationCalculator(ActivityJournalCalculatorMixin, DataFrameCalculatorMixin, MultiProcCalculator):

    def __init__(self, *args, smooth=3, **kargs):
        self.smooth = smooth
        super().__init__(*args, **kargs)

    def _read_dataframe(self, s, ajournal):
        try:
            df = activity_statistics(s, DISTANCE, RAW_ELEVATION, ELEVATION, ALTITUDE,
                                     activity_journal=ajournal, with_timespan=True)
            return df
        except Exception as e:
            log.warning(f'Failed to generate statistics for elevation: {e}')
            raise

    def _calculate_stats(self, s, ajournal, df):
        if not present(df, ELEVATION):
            if present(df, RAW_ELEVATION):
                df = smooth_elevation(df, smooth=self.smooth)
            elif present(df, ALTITUDE):
                log.warning(f'Using {ALTITUDE} as {ELEVATION}')
                df[ELEVATION] = df[ALTITUDE]
            return df
        else:
            return None

    def _copy_results(self, s, ajournal, loader, df):
        for time, row in df.iterrows():
            if ELEVATION in row:
                loader.add(ELEVATION, M, None, ajournal.activity_group, ajournal, row[ELEVATION], time,
                           StatisticJournalFloat,
                           description='An estimate of elevation (may come from various sources).')
            if GRADE in row:
                loader.add(GRADE, PC, None, ajournal.activity_group, ajournal, row[GRADE], time,
                           StatisticJournalFloat,
                           description='The gradient of the smoothed SRTM1 elevation.')
