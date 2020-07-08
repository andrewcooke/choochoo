
from logging import getLogger

from .utils import MultiProcCalculator, ActivityJournalCalculatorMixin, DataFrameCalculatorMixin
from ..pipeline import LoaderMixin
from ...data import Statistics
from ...data.elevation import smooth_elevation
from ...data.frame import present, valid
from ...names import N, Titles, Units
from ...sql import StatisticJournalFloat

log = getLogger(__name__)


class ElevationCalculator(LoaderMixin, ActivityJournalCalculatorMixin, DataFrameCalculatorMixin, MultiProcCalculator):

    def __init__(self, *args, smooth=3, **kargs):
        self.smooth = smooth
        super().__init__(*args, **kargs)

    def _read_dataframe(self, s, ajournal):
        from ..owners import SegmentReader
        try:
            return Statistics(s, activity_journal=ajournal, with_timespan=True). \
                by_name(SegmentReader, N.DISTANCE, N.RAW_ELEVATION, N.ELEVATION, N.ALTITUDE).df
        except Exception as e:
            log.warning(f'Failed to generate statistics for elevation: {e}')
            raise

    def _calculate_stats(self, s, ajournal, df):
        if not present(df, N.ELEVATION):
            if present(df, N.RAW_ELEVATION):
                df = smooth_elevation(df, smooth=self.smooth)
            elif present(df, N.ALTITUDE):
                log.warning(f'Using {N.ALTITUDE} as {N.ELEVATION}')
                df[N.ELEVATION] = df[N.ALTITUDE]
            return df
        else:
            return None

    def _copy_results(self, s, ajournal, loader, df):
        for time, row in df.iterrows():
            if N.ELEVATION in row and valid(row[N.ELEVATION]):
                loader.add(Titles.ELEVATION, Units.M, None, ajournal, row[N.ELEVATION],
                           time, StatisticJournalFloat,
                           description='An estimate of elevation (may come from various sources).')
            if N.GRADE in row and valid(row[N.GRADE]):
                loader.add(Titles.GRADE, Units.PC, None, ajournal, row[N.GRADE],
                           time, StatisticJournalFloat,
                           description='The gradient of the smoothed SRTM1 elevation.')
