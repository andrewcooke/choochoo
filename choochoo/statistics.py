
from collections import deque, Counter

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

    def distance(self):
        if len(self.__waypoints) > 1:
            return self.__waypoints[-1].distance - self.__waypoints[0].distance
        else:
            return 0

    def delta(self):
        if len(self.__waypoints) > 1:
            return self.__waypoints[1].distance - self.__waypoints[0].distance
        else:
            return 0

    def time(self):
        if len(self.__waypoints) > 1:
            return self.__waypoints[-1].epoch - self.__waypoints[0].epoch
        else:
            return 0

    def hrs(self):
        return (waypoint.hr for waypoint in self.__waypoints)

    def __bool__(self):
        return self.delta() > 0


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


class DistanceTimes(Chunks):

    def __init__(self, diary, distance):
        super().__init__(diary)
        self.__distance = distance

    def times(self):
        for chunks in self.chunks():
            distance = sum(chunk.distance() for chunk in chunks)
            if distance > self.__distance:
                while chunks and distance + chunks[0].delta() > self.__distance:
                    distance -= chunks[0].delta()
                    chunks[0].popleft()
                    if not chunks[0]:
                        chunks.popleft()
                time = sum(chunk.time() for chunk in chunks)
                yield time * self.__distance / distance


class Totals(Chunks):

    def __init__(self, diary):
        super().__init__(diary)
        chunks = list(self.chunks())[-1]
        self.distance = sum(chunk.distance() for chunk in chunks)
        self.time = sum(chunk.time() for chunk in chunks)


class Zones(Chunks):

    def __init__(self, diary, zones):
        super().__init__(diary)
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
        times = list(sorted(DistanceTimes(diary, target * 1000).times()))
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
