
from collections import deque, Counter
from itertools import chain

from .squeal.tables.activity import ActivityStatistic, ActivityStatistics, SummaryStatistics, SummaryStatistic
from .squeal.tables.heartrate import HeartRateZones


class Chunk:

    def __init__(self, waypoint):
        self.__timespan = waypoint.activity_timespan
        self.__waypoints = deque([waypoint])

    def append(self, waypoint):
        self.__waypoints.append(waypoint)

    def popleft(self):
        return self.__waypoints.popleft()

    def __diff(self, index, attr):
        if len(self.__waypoints) > 1:
            return attr(self.__waypoints[index]) - attr(self.__waypoints[0])
        else:
            return 0

    def distance(self):
        return self.__diff(-1, lambda w: w.distance)

    def distance_delta(self):
        return self.__diff(1, lambda w: w.distance)

    def time(self):
        return self.__diff(-1, lambda w: w.epoch)

    def time_delta(self):
        return self.__diff(1, lambda w: w.epoch)

    def hrs(self):
        return (waypoint.hr for waypoint in self.__waypoints if waypoint.hr is not None)

    def __len__(self):
        return len(self.__waypoints)

    def __getitem__(self, item):
        return self.__waypoints[item]

    def __bool__(self):
        return self.distance_delta() > 0


class Chunks:

    def __init__(self, log, diary):
        self._log = log
        self.__diary = diary

    def chunks(self):
        chunks, chunk_index = deque(), {}
        for waypoint in self.__diary.waypoints:
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

    def __init__(self, log, diary, distance):
        super().__init__(log, diary)
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

    def __init__(self, log, diary, time, max_gap=None):
        super().__init__(log, diary)
        self.__time = time
        self.__max_gap = 0.01 * time if max_gap is None else max_gap
        log.debug('Will reject gaps > %ds' % int(self.__max_gap))

    def _max_gap(self, chunks):
        return max(c1[0].activity_timespan.start - c2[0].activity_timespan.finish
                   for c1, c2 in zip(list(chunks)[1:], chunks))

    def hrs(self):
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
                hrs = list(sorted(chain(*(chunk.hrs() for chunk in chunks))))
                if hrs:
                    median = len(hrs) // 2
                    yield hrs[median]


class Totals(Chunks):

    def __init__(self, log, diary):
        super().__init__(log, diary)
        chunks = list(self.chunks())[-1]
        self.distance = sum(chunk.distance() for chunk in chunks)
        self.time = sum(chunk.time() for chunk in chunks)


class Zones(Chunks):

    def __init__(self, log, diary, zones):
        super().__init__(log, diary)
        # this assumes record data are evenly distributed
        self.zones = []
        chunks = list(self.chunks())[-1]
        counts = Counter()
        lower = 0
        for zone, upper in enumerate(zone.upper for zone in zones.zones):
            for chunk in chunks:
                for hr in chunk.hrs():
                    if hr is not None:
                        if lower <= hr < upper:
                            counts[zone] += 1
            lower = upper
        total = sum(counts.values())
        if total:
            for zone in range(len(zones.zones)):
                self.zones.append((zone + 1, counts[zone] / total))


def round_km():
    yield from range(5, 21, 5)
    yield from range(25, 76, 25)
    yield from range(100, 251, 50)
    yield from range(300, 1001, 100)


def add_stat(log, session, diary, name, best, value, units):
    statistics = session.query(ActivityStatistics).filter(
        ActivityStatistics.name == name, ActivityStatistics.activity == diary.activity).one_or_none()
    if not statistics:
        statistics = ActivityStatistics(activity=diary.activity, name=name, units=units, best=best)
        session.add(statistics)
    statistic = ActivityStatistic(activity_statistics=statistics, activity_diary=diary, value=value)
    session.add(statistic)
    log.info(statistic)


def add_stats(log, session, diary):
    totals = Totals(log, diary)
    add_stat(log, session, diary, 'Active distance', 'max', totals.distance, 'm')
    add_stat(log, session, diary, 'Active time', 'max', totals.time, 's')
    add_stat(log, session, diary, 'Active speed', 'max', totals.distance * 3.6 / totals.time, 'km/h')
    for target in round_km():
        times = list(sorted(TimeForDistance(log, diary, target * 1000).times()))
        if not times:
            break
        median = len(times) // 2
        add_stat(log, session, diary, 'Median %dkm time' % target, 'min', times[median], 's')
    zones = session.query(HeartRateZones).filter(HeartRateZones.date <= diary.date)\
        .order_by(HeartRateZones.date.desc()).limit(1).one_or_none()
    if zones:
        for (zone, frac) in Zones(log, diary, zones).zones:
            add_stat(log, session, diary, 'Percent in Z%d' % zone, None, 100 * frac, '%')
        for (zone, frac) in Zones(log, diary, zones).zones:
            add_stat(log, session, diary, 'Time in Z%d' % zone,  None, frac * totals.time, 's')
        for target in (5, 10, 15, 20, 30, 60, 90, 120, 180):
            hrs = sorted(MedianHRForTime(log, diary, target * 60).hrs(), reverse=True)
            if hrs:
                add_stat(log, session, diary, 'Max med HR over %dm' % target, 'max', hrs[0], 'bpm')
    else:
        log.warn('No HR zones defined for %s or before' % diary.date)


def add_summary_stats(log, session):
    for statistics in session.query(ActivityStatistics).all():
        if statistics.best:
            values = sorted(statistics.statistics, reverse=(statistics.best == 'max'), key=lambda s: s.value)
            if values:
                name = '%s(%s)' % (statistics.best, statistics.name)
                summary = session.query(SummaryStatistics).filter(SummaryStatistics.name == name).one_or_none()
                if summary:
                    session.delete(summary)
                summary = SummaryStatistics(activity=statistics.activity,
                                            activity_statistics=statistics, name=name)
                session.add(summary)
                for rank in range(min(len(values), 3)):
                    session.add(SummaryStatistic(summary_statistics=summary, activity_statistic=values[rank],
                                                 rank=rank+1))
                log.info(summary)

def add_activity_percentiles(log, session, activity):
    for statistics in session.query(ActivityStatistics).all():
        if statistics.best:
            values = sorted(statistics.statistics, reverse=(statistics.best == 'max'), key=lambda s: s.value)
            if values:
                name = 'Percentile(%s)' %  statistics.name
                statistics = session.query(ActivityStatistics).filter(ActivityStatistics.name == name).one_or_none()
                if statistics:
                    # for statistic in statistics.statistics:
                    #     session.delete(statistic)
                    session.delete(statistics)
                statistics = ActivityStatistics(activity=activity, units='', name=name)
                session.add(statistics)
                for rank, value in enumerate(values, start=1):
                    percentile = 100 * rank / len(values)
                    session.add(ActivityStatistic(activity_statistics=statistics, activity_diary=value.activity_diary,
                                                  value=percentile))
                log.info(statistics)
