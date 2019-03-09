
from sqlalchemy import not_
from sqlalchemy.sql.functions import count

from . import WaypointCalculator
from ..names import SEGMENT_TIME, LATITUDE, LONGITUDE, DISTANCE, S, summaries, MIN, MSR, CNT, HEART_RATE, \
    SEGMENT_HEART_RATE, BPM, MAX
from ..waypoint import filter_none
from ...squeal import ActivityJournal, SegmentJournal, Segment, StatisticName, StatisticJournal, \
    StatisticJournalFloat, Timestamp


class SegmentStatistics(WaypointCalculator):

    def run(self):
        with self._db.session_context() as s:
            SegmentJournal.clean(s)
            if 0 == s.query(count(Segment.id)).scalar():
                self._log.warning('No segments defined in database')
                return
        super().run()

    def _activity_journals_with_missing_data(self, s, activity_group):
        # extends superclass with restriction on activities that have a segment
        existing_ids = s.query(Timestamp.key). \
            filter(Timestamp.owner == self,
                   Timestamp.constraint == activity_group).cte()
        segment_ids = s.query(SegmentJournal.activity_journal_id). \
            join(Segment). \
            filter(Segment.activity_group == activity_group).cte()
        yield from s.query(ActivityJournal). \
            filter(not_(ActivityJournal.id.in_(existing_ids)),
                   ActivityJournal.id.in_(segment_ids),
                   ActivityJournal.activity_group == activity_group).all()

    def _constrain_source(self, s, q, agroup):
        cte = s.query(SegmentJournal.id).join(Segment).filter(Segment.activity_group_id == agroup.id).cte()
        return q.filter(StatisticJournal.source_id.in_(cte))

    def _names(self):
        return {LATITUDE: 'lat',
                LONGITUDE: 'lon',
                DISTANCE: 'distance',
                HEART_RATE: 'hr'}

    def _add_stats_from_waypoints(self, s, ajournal, waypoints):
        for sjournal in s.query(SegmentJournal). \
                filter(SegmentJournal.activity_journal == ajournal).all():
            StatisticJournalFloat.add(self._log, s, SEGMENT_TIME, S, summaries(MIN, CNT, MSR), self,
                                      sjournal.segment, sjournal,
                                      (sjournal.finish - sjournal.start).total_seconds(), sjournal.start)
            waypoints = [w for w in filter_none(self._names().values(), waypoints)
                         if sjournal.start <= w.time <= sjournal.finish]
            # weight by time gap so we don't bias towards more sampled times
            gaps = [(w1.time - w0.time, 0.5 * (w0.hr + w1.hr))
                    for w0, w1 in zip(waypoints, waypoints[1:])]
            if gaps:
                weighted = sum(dt.total_seconds() * hr for dt, hr in gaps)
                average = weighted / sum(dt.total_seconds() for dt, _ in gaps)
                StatisticJournalFloat.add(self._log, s, SEGMENT_HEART_RATE, BPM, summaries(MAX, CNT, MSR), self,
                                          sjournal.segment, sjournal, average, sjournal.start)
            else:
                self._log.warning('No Heart Rate data')

    def _delete_my_statistics(self, s, activity_group):
        start, finish = self._start_finish()
        s.commit()   # so that we don't have any risk of having something in the session that can be deleted
        statistic_name_ids = s.query(StatisticName.id). \
            filter(StatisticName.owner == self).cte()
        segment_journal_ids = s.query(SegmentJournal.id).join(Segment). \
            filter(Segment.activity_group == activity_group).cte()
        for repeat in range(2):
            if repeat:
                q = s.query(StatisticJournal)
            else:
                q = s.query(count(StatisticJournal.id))
            q = q.filter(StatisticJournal.statistic_name_id.in_(statistic_name_ids),
                         StatisticJournal.source_id.in_(segment_journal_ids))
            if start:
                q = q.filter(StatisticJournal.time >= start)
            if finish:
                q = q.filter(StatisticJournal.time < finish)
            self._log.debug(q)
            if repeat:
                q.delete(synchronize_session=False)
            else:
                n = q.scalar()
                if n:
                    self._log.warning('Deleting %d statistics for %s' % (n, activity_group))
                else:
                    self._log.warning('No statistics to delete for %s' % activity_group)
        s.commit()
