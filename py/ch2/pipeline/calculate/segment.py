
from logging import getLogger

from .calculate import MultiProcCalculator, SegmentJournalCalculatorMixin, DataFrameCalculatorMixin
from ...names import SEGMENT_TIME, S, summaries, MIN, MSR, CNT, HEART_RATE, SEGMENT_HEART_RATE, BPM, MAX
from ...data import activity_statistics, present, linear_resample_time
from ...sql import SegmentJournal, StatisticJournalFloat

log = getLogger(__name__)

SJOURNAL = 'sjournal'


class SegmentCalculator(SegmentJournalCalculatorMixin, DataFrameCalculatorMixin, MultiProcCalculator):

    def _delete(self, s):
        super()._delete(s)
        SegmentJournal.clean(s)

    def _read_dataframe(self, s, sjournal):
        return activity_statistics(s, HEART_RATE, activity_journal=sjournal.activity_journal)

    def _calculate_stats(self, s, sjournal, df):
        stats = {SJOURNAL: sjournal,
                 SEGMENT_TIME: (sjournal.finish - sjournal.start).total_seconds()}
        if present(df, HEART_RATE):
            ldf = linear_resample_time(df, start=sjournal.start, finish=sjournal.finish)
            stats[SEGMENT_HEART_RATE] = ldf[HEART_RATE].mean()
        return stats

    def _copy_results(self, s, ajournal, loader, stats):
        sjournal = stats[SJOURNAL]
        loader.add(SEGMENT_TIME, S, summaries(MIN, CNT, MSR), sjournal.segment, sjournal,
                   stats[SEGMENT_TIME], sjournal.start, StatisticJournalFloat)
        if SEGMENT_HEART_RATE in stats:
            loader.add(SEGMENT_HEART_RATE, BPM, summaries(MAX, CNT, MSR), sjournal.segment, sjournal,
                       stats[SEGMENT_HEART_RATE], sjournal.start, StatisticJournalFloat)
