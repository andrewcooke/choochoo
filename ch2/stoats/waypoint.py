
import datetime as dt
from collections import deque, namedtuple
from logging import getLogger

from sqlalchemy import select, and_
from sqlalchemy.sql.functions import coalesce

from ..squeal.tables.statistic import StatisticName, StatisticJournal, StatisticJournalInteger, StatisticJournalFloat
from ..squeal.utils import tables

log = getLogger(__name__)


def make_waypoint(names, extra=None):
    names = list(names)
    if extra:
        names += [extra]
    names = ['time'] + names
    defaults = [None] * len(names)
    return namedtuple('Waypoint', names, defaults=defaults)


class WaypointReader:

    def __init__(self, with_timespan=True):
        self._with_timespan = with_timespan

    def read(self, s, ajournal, names, owner=None, start=None, finish=None):

        t = tables(StatisticName, StatisticJournal, StatisticJournalInteger, StatisticJournalFloat)

        id_map = self._id_map(s, ajournal, names, owner=owner)
        ids = list(id_map.keys())

        Waypoint = make_waypoint(names.values(), extra='timespan' if self._with_timespan else None)

        for timespan in ajournal.timespans:
            log.debug('%s' % timespan)
            # log.debug(f'{timespan.start.timestamp()} - {timespan.finish.timestamp()}')
            waypoint = None
            stmt = select([t.StatisticName.c.id,
                           t.StatisticJournal.c.time,
                           coalesce(t.StatisticJournalFloat.c.value,
                                    t.StatisticJournalInteger.c.value)]) \
                .select_from(t.StatisticJournal.
                             join(t.StatisticName).
                             outerjoin(t.StatisticJournalFloat).
                             outerjoin(t.StatisticJournalInteger)) \
                .where(and_(t.StatisticJournal.c.source_id == ajournal.id,
                            t.StatisticName.c.id.in_(ids),
                            t.StatisticJournal.c.time >= timespan.start,
                            t.StatisticJournal.c.time <= timespan.finish)) \
                .order_by(t.StatisticJournal.c.time)
            if start:
                stmt = stmt.where(t.StatisticJournal.c.time >= start)
            if finish:
                stmt = stmt.where(t.StatisticJournal.c.time <= finish)
            # log.debug(stmt)
            for id, time, value in s.connection().execute(stmt):
                if waypoint and waypoint.time != time:
                    # log.debug(waypoint)
                    yield waypoint
                    waypoint = None
                if not waypoint:
                    waypoint = Waypoint(time=time)
                    if self._with_timespan:
                        waypoint = waypoint._replace(timespan=timespan)
                waypoint = waypoint._replace(**{id_map[id]: value})
        log.debug('Waypoints generated')

    def _id_map(self, s, ajournal, names, owner):
        # need to convert from statistic_name_id to attribute name
        return dict((self._id(s, ajournal, key, owner), value) for key, value in names.items())

    def _id(self, s, ajournal, name, owner=None):
        from ..data.frame import _add_constraint
        q = s.query(StatisticName.id). \
            filter(StatisticName.name == name, StatisticName.constraint == ajournal.activity_group)
        if owner:
            q = _add_constraint(q, StatisticName.owner, owner.split(','), name)
        return q.scalar()


class Chunk:
    '''
    A collection of data points in time order, associated with a single timespan.

    In most of uses the contents are slowly incremented over time (and values popped off the front)
    as various statistics are calculated.
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

    def values(self, name):
        index = self.__waypoints[0]._fields.index(name)
        return (waypoint[index] for waypoint in self.__waypoints if waypoint[index] is not None)

    def __len__(self):
        return len(self.__waypoints)

    def __getitem__(self, item):
        return self.__waypoints[item]

    def __bool__(self):
        return self.distance() > 0


class Chunks:
    '''
    This returns a sequence of lists of chunks, with progressively more waypoints.  The chunks are
    the *same* list, but with more points added each time (ie mutated / extended),

    The caller should read chunks until they contain sufficient data (for whatever is being calculated)
    and then discard and call to maintain the same data length.
    '''

    def __init__(self, waypoints):
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
    return [w for w in waypoints if all(n in w._fields and getattr(w, n) is not None for n in names)]
