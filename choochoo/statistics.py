
from collections import deque, Counter
from itertools import chain

from .squeal.tables.activity import ActivityStatistic
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
        return (waypoint.hr for waypoint in self.__waypoints)

    def __len__(self):
        return len(self.__waypoints)

    def __getitem__(self, item):
        return self.__waypoints[item]

    def __bool__(self):
        return self.distance_delta() > 0


class Chunks:

    def __init__(self, diary):
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

    def __init__(self, diary, distance):
        super().__init__(diary)
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

    def __init__(self, diary, time, max_gap=None):
        super().__init__(diary)
        self.__time = time
        self.__max_gap = 0.1 * time if max_gap is None else max_gap

    def _max_gap(self, chunks):
        return max(c1[0].activity_timespan.start - c2[0].activity_timespan.finish
                   for c1, c2 in zip(list(chunks)[1:], chunks))

    def hrs(self):
        for chunks in self.chunks():
            while len(chunks) > 1 and self._max_gap(chunks) > self.__max_gap:
                chunks.popleft()
            time = sum(chunk.time() for chunk in chunks)
            if time > self.__time:
                while chunks and time - chunks[0].time_delta() > self.__time:
                    time -= chunks[0].time_delta()
                    chunks[0].popleft()
                    if not chunks[0]:
                        chunks.popleft()
                hrs = list(sorted(chain(*(chunk.hrs() for chunk in chunks))))
                median = len(hrs) // 2
                yield hrs[median]


class Totals(Chunks):

    def __init__(self, diary):
        super().__init__(diary)
        chunks = list(self.chunks())[-1]
        self.distance = sum(chunk.distance() for chunk in chunks)
        self.time = sum(chunk.time() for chunk in chunks)


class Zones(Chunks):

    def __init__(self, diary, zones):
        super().__init__(diary)
        # this assumes record data are evenly distributed
        chunks = list(self.chunks())[-1]
        counts = Counter()
        lower = 0
        for zone, upper in enumerate(zone.upper for zone in zones.zones):
            for chunk in chunks:
                for hr in chunk.hrs():
                    if lower <= hr < upper:
                        counts[zone] += 1
            lower = upper
        total = sum(counts.values())
        self.zones = []
        for zone in range(len(zones.zones)):
            self.zones.append((zone + 1, counts[zone] / total))


def round_km():
    yield from range(5, 21, 5)
    yield from range(25, 76, 25)
    yield from range(100, 251, 50)
    yield from range(300, 1001, 100)


def add_stat(log, session, diary, name, value, units):
    statistic = ActivityStatistic(activity_diary=diary, name=name, value=value, units=units)
    session.add(statistic)
    log.info(statistic)


def add_stats(log, session, diary):
    totals = Totals(diary)
    add_stat(log, session, diary, 'Active distance', totals.distance, 'm')
    add_stat(log, session, diary, 'Active time', totals.time, 's')
    add_stat(log, session, diary, 'Active speed', totals.distance * 3.6 / totals.time, 'km/h')
    for target in round_km():
        times = list(sorted(TimeForDistance(diary, target * 1000).times()))
        if not times:
            break
        median = len(times) // 2
        add_stat(log, session, diary, 'Median %dkm time' % target, times[median], 's')
    zones = session.query(HeartRateZones).filter(HeartRateZones.date <= diary.date)\
        .order_by(HeartRateZones.date).limit(1).one_or_none()
    if zones:
        for (zone, frac) in Zones(diary, zones).zones:
            add_stat(log, session, diary, 'Percent in Z%d' % zone, 100 * frac, '%')
        for (zone, frac) in Zones(diary, zones).zones:
            add_stat(log, session, diary, 'Time in Z%d' % zone, frac * totals.time, 's')
    for target in (5, 10, 20, 30, 60, 90, 120, 180):
        hrs = sorted(MedianHRForTime(diary, target * 60).hrs(), reverse=True)
        if not hrs:
            break
        add_stat(log, session, diary, 'Max med HR over %dm' % target, hrs[0], 'bpm')
