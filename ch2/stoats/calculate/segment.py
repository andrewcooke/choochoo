from logging import getLogger

from sqlalchemy import not_

from . import ActivityJournalCalculatorMixin, WaypointCalculatorMixin, MultiProcCalculator
from ..names import SEGMENT_TIME, LATITUDE, LONGITUDE, DISTANCE, S, summaries, MIN, MSR, CNT, HEART_RATE, \
    SEGMENT_HEART_RATE, BPM, MAX
from ..waypoint import filter_none
from ...squeal import ActivityJournal, SegmentJournal, StatisticJournalFloat, Timestamp

log = getLogger(__name__)


class SegmentCalculator(ActivityJournalCalculatorMixin, WaypointCalculatorMixin, MultiProcCalculator):

    def _names(self):
        return {LATITUDE: 'lat',
                LONGITUDE: 'lon',
                DISTANCE: 'distance',
                HEART_RATE: 'hr'}

    def _missing(self, s):
        # extends superclass with restriction on activities that have a segment
        existing_ids = s.query(Timestamp.key). \
            filter(Timestamp.owner == self.owner_out)
        segment_ids = s.query(SegmentJournal.activity_journal_id)
        q = s.query(ActivityJournal.start). \
            filter(not_(ActivityJournal.id.in_(existing_ids)),
                   ActivityJournal.id.in_(segment_ids))
        return [row[0] for row in self._delimit_query(q)]

    def _calculate_results(self, s, ajournal, waypoints, loader):
        for sjournal in s.query(SegmentJournal). \
                filter(SegmentJournal.activity_journal == ajournal).all():
            loader.add(SEGMENT_TIME, S, summaries(MIN, CNT, MSR), sjournal.segment, sjournal,
                       (sjournal.finish - sjournal.start).total_seconds(), sjournal.start, StatisticJournalFloat)
            waypoints = [w for w in filter_none(self._names().values(), waypoints)
                         if sjournal.start <= w.time <= sjournal.finish]
            # weight by time gap so we don't bias towards more sampled times
            gaps = [(w1.time - w0.time, 0.5 * (w0.hr + w1.hr))
                    for w0, w1 in zip(waypoints, waypoints[1:])]
            if gaps:
                weighted = sum(dt.total_seconds() * hr for dt, hr in gaps)
                average = weighted / sum(dt.total_seconds() for dt, _ in gaps)
                loader.add(SEGMENT_HEART_RATE, BPM, summaries(MAX, CNT, MSR), sjournal.segment, sjournal,
                           average, sjournal.start, StatisticJournalFloat)
            else:
                log.warning('No Heart Rate data')
