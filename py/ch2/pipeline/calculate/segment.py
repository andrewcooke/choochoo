
from logging import getLogger

from .utils import ProcessCalculator, SegmentJournalCalculatorMixin, DataFrameCalculatorMixin
from ..pipeline import OwnerInMixin, LoaderMixin
from ...data import present, linear_resample_time, Statistics
from ...names import N, T, S, U
from ...sql import StatisticJournalType

log = getLogger(__name__)

SJOURNAL = 'sjournal'


class SegmentCalculator(LoaderMixin, OwnerInMixin,
                        SegmentJournalCalculatorMixin, DataFrameCalculatorMixin, ProcessCalculator):

    def _startup(self, s):
        super()._startup(s)
        self._provides(s, T.SEGMENT_TIME, StatisticJournalType.FLOAT, U.S, S.join(S.MIN, S.CNT, S.MSR),
                       'The time to complete the segment.')
        self._provides(s, T.SEGMENT_HEART_RATE, StatisticJournalType.FLOAT, U.S, S.join(S.MAX, S.CNT, S.MSR),
                       'The average heart rate for the segment.')

    def _read_dataframe(self, s, sjournal):
        from ch2.pipeline.read.segment import SegmentReader
        return Statistics(s, activity_journal=sjournal.activity_journal). \
            by_name(SegmentReader, N.HEART_RATE).df

    def _calculate_stats(self, s, sjournal, df):
        stats = {SJOURNAL: sjournal,
                 N.SEGMENT_TIME: (sjournal.finish - sjournal.start).total_seconds()}
        if present(df, N.HEART_RATE):
            ldf = linear_resample_time(df, start=sjournal.start, finish=sjournal.finish)
            stats[N.SEGMENT_HEART_RATE] = ldf[N.HEART_RATE].mean()
        return stats

    def _copy_results(self, s, ajournal, loader, stats):
        sjournal = stats.pop(SJOURNAL)
        for name in stats:
            loader.add_data(name, sjournal, stats[name], sjournal.start)
