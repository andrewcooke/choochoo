
from logging import getLogger

from .calculate import MultiProcCalculator, SegmentJournalCalculatorMixin, DataFrameCalculatorMixin
from ...names import Names, Titles, Summaries as S, summaries, Units
from ...data import activity_statistics, present, linear_resample_time
from ...sql import SegmentJournal, StatisticJournalFloat

log = getLogger(__name__)

SJOURNAL = 'sjournal'


class SegmentCalculator(SegmentJournalCalculatorMixin, DataFrameCalculatorMixin, MultiProcCalculator):

    def _delete(self, s):
        super()._delete(s)
        SegmentJournal.clean(s)

    def _read_dataframe(self, s, sjournal):
        return activity_statistics(s, Names.HEART_RATE, activity_journal=sjournal.activity_journal)

    def _calculate_stats(self, s, sjournal, df):
        stats = {Titles.SJOURNAL: sjournal,
                 Titles.SEGMENT_TIME: (sjournal.finish - sjournal.start).total_seconds()}
        if present(df, Names.HEART_RATE):
            ldf = linear_resample_time(df, start=sjournal.start, finish=sjournal.finish)
            stats[Titles.SEGMENT_HEART_RATE] = ldf[Names.HEART_RATE].mean()
        return stats

    def _copy_results(self, s, ajournal, loader, stats):
        sjournal = stats[SJOURNAL]
        loader.add(Titles.SEGMENT_TIME, Units.S, summaries(S.MIN, S.CNT, S.MSR), sjournal.segment, sjournal,
                   stats[Names.SEGMENT_TIME], sjournal.start, StatisticJournalFloat)
        if Titles.SEGMENT_HEART_RATE in stats:
            loader.add(Titles.SEGMENT_HEART_RATE, Units.BPM, summaries(S.MAX, S.CNT, S.MSR), sjournal.segment,
                       sjournal, stats[Titles.SEGMENT_HEART_RATE], sjournal.start, StatisticJournalFloat)
