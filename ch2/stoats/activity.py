
import datetime as dt
from collections.__init__ import deque, Counter
from itertools import chain

from sqlalchemy.sql.functions import count

from .names import ACTIVE_DISTANCE, MAX, M, ACTIVE_TIME, S, ACTIVE_SPEED, KMH, round_km, MEDIAN_KM_TIME, \
    PERCENT_IN_Z, PC, TIME_IN_Z, HR_MINUTES, MAX_MED_HR_OVER_M, BPM
from ..squeal.tables.activity import Activity, ActivityJournal
from ..squeal.tables.source import Source
from ..squeal.tables.statistic import StatisticJournalFloat, StatisticJournal, Statistic
from ..stoats.heart_rate import hr_zones


class ActivityStatistics:

    def __init__(self, log, db):
        self._log = log
        self._db = db

    def run(self, force=False, after=None):
        with self._db.session_context() as s:
            for activity in s.query(Activity).all():
                self._log.debug('Checking statistics for activity %s' % activity.name)
                if force:
                    self._delete_activity(s, activity, after=after)
                self._run_activity(s, activity)

    def _delete_activity(self, s, activity, after=None):
        # we can't delete the source because that's the activity journal.
        # so instead we wipe all statistics that are owned by us.
        # we do this in SQL for speed, but are careful to use the parent node.
        for repeat in range(2):
            if repeat:
                q = s.query(StatisticJournal)
            else:
                q = s.query(count(StatisticJournal.id))
            q = q.join(Statistic, Source, ActivityJournal). \
                filter(Statistic.owner == self,
                       ActivityJournal.activity == activity)
            if after:
                q = q.filter(Source.time >= after)
            if repeat:
                for journal in q.all():
                    self._log.debug('Deleting %s (%s)' % (journal, journal.statistic))
                    s.delete(journal)
            else:
                n = q.scalar()
                if n:
                    self._log.warn('Deleting %d statistics for %s' % (n, activity))
                else:
                    self._log.warn('No statistics to delete for %s' % activity)

    def _run_activity(self, s, activity):
        for journal in s.query(ActivityJournal).outerjoin(Activity, StatisticJournal). \
                filter(Activity.id == activity.id,
                       StatisticJournal.source == None).all():
            self._log.info('Adding statistics for %s' % journal)
            self._add_stats(s, journal, activity)

    def _add_stats(self, s, journal, activity):
        totals = Totals(self._log, journal)
        self._add_float_stat(s, journal, activity, ACTIVE_DISTANCE, MAX, totals.distance, M)
        self._add_float_stat(s, journal, activity, ACTIVE_TIME, MAX, totals.time, S)
        self._add_float_stat(s, journal, activity, ACTIVE_SPEED, MAX, totals.distance * 3.6 / totals.time, KMH)
        for target in round_km():
            times = list(sorted(TimeForDistance(self._log, journal, target * 1000).times()))
            if not times:
                break
            median = len(times) // 2
            self._add_float_stat(s, journal, activity, MEDIAN_KM_TIME % target, 'min', times[median], S)
        zones = hr_zones(self._log, s, activity, journal.time)
        if zones:
            for (zone, frac) in Zones(self._log, journal, zones).zones:
                self._add_float_stat(s, journal, activity, PERCENT_IN_Z % zone, None, 100 * frac, PC)
            for (zone, frac) in Zones(self._log, journal, zones).zones:
                self._add_float_stat(s, journal, activity, TIME_IN_Z % zone, None, frac * totals.time, S)
            for target in HR_MINUTES:
                heart_rates = sorted(MedianHRForTime(self._log, journal, target * 60).heart_rates(), reverse=True)
                if heart_rates:
                    self._add_float_stat(s, journal, activity, MAX_MED_HR_OVER_M % target, MAX, heart_rates[0], BPM)
        else:
            self._log.warn('No HR zones defined for %s or before' % journal.time)

    def _add_float_stat(self, s, journal, activity, name, summary, value, units):
        StatisticJournalFloat.add(self._log, s, name, units, summary, self, activity.id, journal, value)


class Chunk:

    def __init__(self, waypoint):
        self.__timespan = waypoint.activity_timespan
        self.__waypoints = deque([waypoint])

    def append(self, waypoint):
        self.__waypoints.append(waypoint)

    def popleft(self):
        return self.__waypoints.popleft()

    def __diff(self, index, attr, zero=0):
        if len(self.__waypoints) > 1:
            return attr(self.__waypoints[index]) - attr(self.__waypoints[0])
        else:
            return zero

    def distance(self):
        return self.__diff(-1, lambda w: w.distance)

    def distance_delta(self):
        return self.__diff(1, lambda w: w.distance)

    def time(self):
        return self.__diff(-1, lambda w: w.time, dt.timedelta(0)).total_seconds()

    def time_delta(self):
        return self.__diff(1, lambda w: w.time, dt.timedelta(0)).total_seconds()

    def heart_rates(self):
        return (waypoint.heart_rate for waypoint in self.__waypoints if waypoint.heart_rate is not None)

    def __len__(self):
        return len(self.__waypoints)

    def __getitem__(self, item):
        return self.__waypoints[item]

    def __bool__(self):
        return self.distance_delta() > 0


class Chunks:

    def __init__(self, log, journal):
        self._log = log
        self.__journal = journal

    def chunks(self):
        chunks, chunk_index = deque(), {}
        for waypoint in self.__journal.waypoints:
            timespan = waypoint.activity_timespan
            if timespan:
                if timespan in chunk_index:
                    chunk_index[timespan].append(waypoint)
                else:
                    chunk = Chunk(waypoint)
                    chunk_index[timespan] = chunk
                    chunks.append(chunk)
                yield chunks


class TimeForDistance(Chunks):

    def __init__(self, log, journal, distance):
        super().__init__(log, journal)
        self.__distance = distance

    def times(self):
        for chunks in self.chunks():
            distance = sum(chunk.distance() for chunk in chunks)
            if distance > self.__distance:
                while chunks and distance - chunks[0].distance_delta() > self.__distance:
                    distance -= chunks[0].distance_delta()
                    chunks[0].popleft()
                    if not chunks[0]:
                        chunks.popleft()
                time = sum(chunk.time() for chunk in chunks)
                yield time * self.__distance / distance


class MedianHRForTime(Chunks):

    def __init__(self, log, journal, time, max_gap=None):
        super().__init__(log, journal)
        self.__time = time
        self.__max_gap = 0.01 * time if max_gap is None else max_gap
        log.debug('Will reject gaps > %ds' % int(self.__max_gap))

    def _max_gap(self, chunks):
        return max(c1[0].activity_timespan.start - c2[0].activity_timespan.finish
                   for c1, c2 in zip(list(chunks)[1:], chunks)).total_seconds()

    def heart_rates(self):
        for chunks in self.chunks():
            while len(chunks) > 1 and self._max_gap(chunks) > self.__max_gap:
                self._log.debug('Rejecting chunk because of gap (%ds)' % int(self._max_gap(chunks)))
                chunks.popleft()
            time = sum(chunk.time() for chunk in chunks)
            if time > self.__time:
                while chunks and time - chunks[0].time_delta() > self.__time:
                    time -= chunks[0].time_delta()
                    chunks[0].popleft()
                    while chunks and not chunks[0]:
                        chunks.popleft()
                heart_rates = list(sorted(chain(*(chunk.heart_rates() for chunk in chunks))))
                if heart_rates:
                    median = len(heart_rates) // 2
                    yield heart_rates[median]


class Totals(Chunks):

    def __init__(self, log, journal):
        super().__init__(log, journal)
        chunks = list(self.chunks())[-1]
        self.distance = sum(chunk.distance() for chunk in chunks)
        self.time = sum(chunk.time() for chunk in chunks)


class Zones(Chunks):

    def __init__(self, log, journal, zones):
        super().__init__(log, journal)
        # this assumes record data are evenly distributed
        self.zones = []
        chunks = list(self.chunks())[-1]
        counts = Counter()
        lower_limit = 0
        for zone, upper_limit in enumerate(zones):
            for chunk in chunks:
                for heart_rate in chunk.heart_rates():
                    if heart_rate is not None:
                        if lower_limit <= heart_rate < upper_limit:
                            counts[zone] += 1
            lower_limit = upper_limit
        total = sum(counts.values())
        if total:
            for zone in range(len(zones)):
                self.zones.append((zone + 1, counts[zone] / total))


