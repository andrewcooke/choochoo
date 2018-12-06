
from sqlalchemy.sql.functions import count

from . import WaypointCalculator
from ..names import SEGMENT_TIME, LATITUDE, LONGITUDE, DISTANCE, S, summaries, MIN, MSR, CNT
from ...squeal.tables.segment import SegmentJournal, Segment
from ...squeal.tables.statistic import StatisticName, StatisticJournal, StatisticJournalType


class SegmentStatistics(WaypointCalculator):

    def run(self, force=False, after=None, **run_kargs):
        with self._db.session_context() as s:
            if 0 == s.query(count(Segment.id)).scalar():
                self._log.warn('No segments defined')
                return
        super().run(force=force, after=after, **run_kargs)

    def _filter_statistic_journals(self, q):
        return q.filter(StatisticName.name == SEGMENT_TIME)

    def _filter_activity_journals(self, q):
        return q.join(SegmentJournal)

    def _names(self):
        return {LATITUDE: 'lat',
                LONGITUDE: 'lon',
                DISTANCE: 'distance'}

    def _add_stats_from_waypoints(self, s, ajournal, waypoints):
        for sjournal in s.query(SegmentJournal). \
                filter(SegmentJournal.activity_journal == ajournal).all():
            start, finish = self._find_ends(waypoints, sjournal)
            tstart = waypoints[start].time.timestamp() * sjournal.start_weight + \
                     waypoints[start-1].time.timestamp() * (1 - sjournal.start_weight)
            tfinish = waypoints[finish].time.timestamp() * sjournal.finish_weight + \
                      waypoints[finish+1].time.timestamp() * (1 - sjournal.finish_weight)
            StatisticJournal.add(self._log, s, SEGMENT_TIME, S, summaries(MIN, CNT, MSR), self,
                                 ajournal.activity_group, ajournal, tfinish - tstart, tstart,
                                 StatisticJournalType.FLOAT)
            self._log.info('Added %s for %s on %s' % (SEGMENT_TIME, sjournal.segment.name, sjournal.start_time))

    def _find_ends(self, waypoints, sjournal):
        start, finish = None, None
        for i, waypoint in enumerate(waypoints):
            if sjournal.start_time == waypoint.time:
                start = i
            if sjournal.finish_time == waypoint.time:
                finish = i
        if start is None or finish is None:
            import pdb; pdb.set_trace()
            raise Exception('Bad time')
        return start, finish
