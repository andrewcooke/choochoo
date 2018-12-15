
import datetime as dt
from collections import deque

from sqlalchemy import inspect, select, and_
from sqlalchemy.sql.functions import coalesce

from ..lib.data import AttrDict
from ..squeal.tables.statistic import StatisticName, StatisticJournal, StatisticJournalInteger, StatisticJournalFloat


class WaypointReader:

    def __init__(self, log, with_timespan=True):
        self._log = log
        self._with_timespan = with_timespan

    def read(self, s, ajournal, names, owner):

        sn = inspect(StatisticName).local_table
        sj = inspect(StatisticJournal).local_table
        sji = inspect(StatisticJournalInteger).local_table
        sjf = inspect(StatisticJournalFloat).local_table

        id_map = self._id_map(s, ajournal, names, owner)
        ids = list(id_map.keys())

        for timespan in ajournal.timespans:
            self._log.debug('%s' % timespan)
            waypoint = None
            stmt = select([sn.c.id, sj.c.time, coalesce(sjf.c.value, sji.c.value)]) \
                .select_from(sj.join(sn).outerjoin(sjf).outerjoin(sji)) \
                .where(and_(sj.c.source_id == ajournal.id,
                            sn.c.id.in_(ids),
                            sj.c.time >= timespan.start,
                            sj.c.time <= timespan.finish)) \
                .order_by(sj.c.time)
            self._log.debug(stmt)
            for id, time, value in s.connection().execute(stmt):
                if waypoint and waypoint['time'] != time:
                    yield waypoint
                    waypoint = None
                if not waypoint:
                    waypoint = AttrDict({'time': time})
                    if self._with_timespan:
                        waypoint['timespan'] = timespan
                waypoint[id_map[id]] = value
        self._log.debug('Waypoints generated')

    def _id_map(self, s, ajournal, names, owner):
        # need to convert from statistic_name_id to attribute name
        return dict((self._id(s, ajournal, key, owner), value) for key, value in names.items())

    def _id(self, s, ajournal, name, owner):
        return s.query(StatisticName.id). \
            filter(StatisticName.name == name,
                   StatisticName.owner == owner,
                   StatisticName.constraint == ajournal.activity_group).scalar()


class Chunk:
    '''
    A collection of data points in time order, associated with a single timespan.

    In most of the uses below the contents are slowly incremented over time (and
    values popped off the front) as various statistics are calculated.
    '''

    def __init__(self, waypoint):
        self.__timespan = waypoint.timespan
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
    '''
    This returns a sequence of lists of chunks, with progressively more waypoints.  The chunks are
    the *same* list, but with more points added each time (ie mutated / extended),

    The caller should read chunks until they contain sufficient data (for whatever is being calculated)
    and then discard and call to maintain the same data length.
    '''

    def __init__(self, log, waypoints):
        self._log = log
        self._waypoints = waypoints

    def chunks(self):
        chunks, chunk_index = deque(), {}
        for waypoint in self._waypoints:
            timespan = waypoint.timespan
            if timespan in chunk_index:
                chunk_index[timespan].append(waypoint)
            else:
                chunk = Chunk(waypoint)
                chunk_index[timespan] = chunk
                chunks.append(chunk)
            yield chunks

    def complete(self):
        '''
        The final chunks, containing all waypoints.
        '''
        last = None
        for chunks in self.chunks():
            last = chunks
        return last

    @staticmethod
    def drop_first(chunks):
        chunks[0].popleft()
        while chunks and not chunks[0]:
            chunks.popleft()


def filter_none(names, waypoints):
    names = list(names)
    return [w for w in waypoints if all(n in w and w[n] is not None for n in names)]
