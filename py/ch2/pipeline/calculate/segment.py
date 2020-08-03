
from logging import getLogger

from .utils import ProcessCalculator, SegmentJournalCalculatorMixin, DataFrameCalculatorMixin
from ..pipeline import OwnerInMixin, LoaderMixin
from ...data import present, linear_resample_time, Statistics
from ...names import N, Titles, Summaries as S, Units
from ...sql import SegmentJournal, StatisticJournalFloat

log = getLogger(__name__)

SJOURNAL = 'sjournal'


class SegmentCalculator(LoaderMixin, OwnerInMixin,
                        SegmentJournalCalculatorMixin, DataFrameCalculatorMixin, ProcessCalculator):

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
        sjournal = stats[SJOURNAL]
        loader.add(Titles.SEGMENT_TIME, Units.S, S.join(S.MIN, S.CNT, S.MSR), sjournal,
                   stats[N.SEGMENT_TIME], sjournal.start, StatisticJournalFloat)
        if N.SEGMENT_HEART_RATE in stats:
            loader.add(Titles.SEGMENT_HEART_RATE, Units.BPM, S.join(S.MAX, S.CNT, S.MSR),
                       sjournal, stats[N.SEGMENT_HEART_RATE], sjournal.start, StatisticJournalFloat)
