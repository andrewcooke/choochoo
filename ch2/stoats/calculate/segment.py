
from logging import getLogger

from sqlalchemy import not_

from . import ActivityJournalCalculatorMixin, MultiProcCalculator, DataFrameCalculatorMixin
from ..names import SEGMENT_TIME, S, summaries, MIN, MSR, CNT, HEART_RATE, \
    SEGMENT_HEART_RATE, BPM, MAX
from ...data import activity_statistics, present, linear_resample_time
from ...squeal import ActivityJournal, SegmentJournal, StatisticJournalFloat, Timestamp

log = getLogger(__name__)

SJOURNAL = 'sjournal'


class SegmentCalculator(ActivityJournalCalculatorMixin, DataFrameCalculatorMixin, MultiProcCalculator):

    def _startup(self, s):
        SegmentJournal.clean(s)
        super()._startup(s)

    def _shutdown(self, s):
        SegmentJournal.clean(s)
        super()._shutdown(s)

    def _missing(self, s):
        # extends superclass with restriction on activities that have a segment
        existing_ids = s.query(Timestamp.source_id). \
            filter(Timestamp.owner == self.owner_out)
        activity_ids = s.query(SegmentJournal.activity_journal_id)
        q = s.query(ActivityJournal.start). \
            filter(not_(ActivityJournal.id.in_(existing_ids)),
                   ActivityJournal.id.in_(activity_ids))
        return [row[0] for row in self._delimit_query(q)]

    def _read_dataframe(self, s, ajournal):
        return activity_statistics(s, HEART_RATE, activity_journal=ajournal)

    def _calculate_stats(self, s, ajournal, df):
        all = []
        for sjournal in s.query(SegmentJournal). \
                filter(SegmentJournal.activity_journal == ajournal).all():
            stats = {SJOURNAL: sjournal,
                     SEGMENT_TIME: (sjournal.finish - sjournal.start).total_seconds()}
            if present(df, HEART_RATE):
                ldf = linear_resample_time(df, start=sjournal.start, finish=sjournal.finish)
                stats[SEGMENT_HEART_RATE] = ldf[HEART_RATE].mean()
            all.append(stats)
        return all

    def _copy_results(self, s, ajournal, loader, all):
        for stats in all:
            sjournal = stats[SJOURNAL]
            loader.add(SEGMENT_TIME, S, summaries(MIN, CNT, MSR), sjournal.segment, sjournal,
                       stats[SEGMENT_TIME], sjournal.start, StatisticJournalFloat)
            if SEGMENT_HEART_RATE in stats:
                loader.add(SEGMENT_HEART_RATE, BPM, summaries(MAX, CNT, MSR), sjournal.segment, sjournal,
                           stats[SEGMENT_HEART_RATE], sjournal.start, StatisticJournalFloat)
