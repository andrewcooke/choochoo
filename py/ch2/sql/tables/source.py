
from abc import abstractmethod
from enum import IntEnum
from logging import getLogger

from sqlalchemy import ForeignKey, Column, Integer, func, UniqueConstraint, select, Boolean
from sqlalchemy.event import listens_for
from sqlalchemy.orm import Session, relationship, aliased
from sqlalchemy.sql.functions import count

from ..support import Base
from ..types import OpenSched, Date, ShortCls, short_cls
from ..utils import add
from ...lib.date import to_time, time_to_local_date, max_time, min_time, extend_range
from ...lib.utils import timing

log = getLogger(__name__)


class SourceType(IntEnum):

    SOURCE = 0
    INTERVAL = 1
    ACTIVITY = 2
    DIARY_TOPIC = 3
    CONSTANT = 4
    MONITOR = 5
    SEGMENT = 6
    COMPOSITE = 7
    DUMMY = 8
    ITEM = 9
    MODEL = 10
    ACTIVITY_TOPIC = 11


class Source(Base):

    __tablename__ = 'source'

    id = Column(Integer, primary_key=True)
    type = Column(Integer, nullable=False, index=True)  # index needed for fast deletes of subtypes

    __mapper_args__ = {
        'polymorphic_identity': SourceType.SOURCE,
        'polymorphic_on': type
    }

    @abstractmethod
    def time_range(self, s):
        raise NotImplementedError('time_range for %s' % self)

    @classmethod
    def before_flush(cls, s):
        cls.__clean_dirty_intervals(s)

    @classmethod
    def __clean_dirty_intervals(cls, s):
        from .statistic import StatisticJournal, StatisticJournalText
        # sessions are generally restricted to one time region, so we'll bracket that rather than list all times
        start, finish = None, None
        # all sources except intervals that are being deleted (need to catch on cascade to statistics)
        for instance in s.deleted:
            if isinstance(instance, Source) and not isinstance(instance, Interval):
                a, b = instance.time_range(s)
                start, finish = min_time(a, start), max_time(b, finish)
        # all modified statistics
        for instance in s.dirty:
            # ignore constants as time 0
            # ignore textual values (don't have useful stats and commonly modified fields)
            if isinstance(instance, StatisticJournal) and s.is_modified(instance) and instance.time \
                    and not isinstance(instance, StatisticJournalText):
                start, finish = extend_range(start, finish, instance.time)
        # all new statistics that aren't associated with intervals and have non-null data
        # (avoid triggering on empty diary entries)
        for instance in s.new:
            # ignore constants as time 0
            # ignore textual values
             if isinstance(instance, StatisticJournal) and not isinstance(instance.source, Interval) \
                     and not isinstance(instance.source, Dummy) \
                     and not isinstance(instance.source, StatisticJournalText) \
                     and instance.value is not None and instance.time:
                start, finish = extend_range(start, finish, instance.time)
        if start is not None:
            Interval.mark_dirty_times(s, start, finish)

    @classmethod
    def from_id(cls, s, id):
        return s.query(Source).filter(Source.id == id).one()


@listens_for(Session, 'before_flush')
def before_flush(session, context, instances):
    Source.before_flush(session)


class NoStatistics(Exception):
    pass


class Interval(Source):

    __tablename__ = 'interval'   # would be nice to rename this interval_source at some point

    id = Column(Integer, ForeignKey('source.id', ondelete='cascade'), primary_key=True)
    schedule = Column(OpenSched, nullable=False, index=True)
    # disambiguate creator so each can wipe only its own data on force
    owner = Column(ShortCls, nullable=False)
    # these are for the schedule - finish is redundant (start is not because of timezone issues)
    start = Column(Date, nullable=False, index=True)
    finish = Column(Date, nullable=False, index=True)
    dirty = Column(Boolean, nullable=False, default=False)
    UniqueConstraint(schedule, owner, start)

    __mapper_args__ = {
        'polymorphic_identity': SourceType.INTERVAL
    }

    def __str__(self):
        owner = self.owner if isinstance(self.owner, str) else short_cls(self.owner)
        return 'Interval "%s from %s" (owner %s)' % (self.schedule, self.start, owner)

    @classmethod
    def _raw_statistics_time_range(cls, s, statistics_owner=None):
        '''
        The time range over which statistics exist (optionally restricted by owner),
        ignoring constants at "time zero".  This is the first to the last time for
        any statistics - it pays no attention to gaps.
        '''
        from .statistic import StatisticJournal, StatisticName
        q = s.query(func.min(StatisticJournal.time), func.max(StatisticJournal.time)). \
            filter(StatisticJournal.time > to_time(2 * 24 * 60 * 60.0))
        if statistics_owner:
            q = q.join(StatisticName).filter(StatisticName.owner == statistics_owner)
        start, finish = q.one()   # skip entire first day because tz
        if start and finish:
            return start, finish
        else:
            raise NoStatistics('No statistics are currently defined')

    @classmethod
    def at(cls, s, schedule, interval_owner, start):
        '''
        The existing interval for a given start, owner, schedule.
        '''
        return s.query(Interval). \
            filter(Interval.start == start,
                   Interval.schedule == schedule,
                   Interval.owner == interval_owner).one_or_none()

    @classmethod
    def missing_dates(cls, s, schedule, interval_owner, statistic_owner=None, start=None, finish=None):
        '''
        Previous approach was way too complicated and not thread-safe.  Instead, just enumerate intervals and test.
        '''
        stats_start_time, stats_finish_time = cls._raw_statistics_time_range(s, statistic_owner)
        stats_start = time_to_local_date(stats_start_time)
        stats_finish = time_to_local_date(stats_finish_time)
        log.debug('Statistics (in general) exist %s - %s' % (stats_start, stats_finish))
        start = schedule.start_of_frame(start if start else stats_start)
        finish = finish if finish else schedule.next_frame(stats_finish)
        while start < finish:
            next = schedule.next_frame(start)
            if not cls.at(s, schedule, interval_owner, start):
                yield start, next
            start = next

    @classmethod
    def dirty_all(cls, s):
        log.warning('Dirtying all Intervals')
        s.query(Interval).update({Interval.dirty: True}, synchronize_session=False)

    @classmethod
    def mark_dirty_times(cls, s, start, finish, owner=None):
        '''
        Dirty all intervals that include data in the given TIME range,
        '''
        cls.mark_dirty_dates(s, time_to_local_date(start), time_to_local_date(finish), owner=owner)

    @classmethod
    def mark_dirty_dates(cls, s, start, finish, owner=None):
        '''
        Dirty all summary intervals (not monitor intervals) in the given DATE range.
        '''
        q = s.query(Interval).filter(Interval.start <= finish, Interval.finish > start)
        if owner:
            q = q.filter(Interval.owner == owner)
        q.update({Interval.dirty: True}, synchronize_session=False)

    @classmethod
    def clean(cls, s):
        q = s.query(Interval).filter(Interval.dirty == True)
        log.info(f'Deleting {q.count()} dirty Intervals')
        for interval in q.all():
            s.delete(interval)


class Dummy(Source):

    __tablename__ = 'dummy_source'

    DUMMY = 'Dummy'

    id = Column(Integer, ForeignKey('source.id', ondelete='cascade'), primary_key=True)

    __mapper_args__ = {
        'polymorphic_identity': SourceType.DUMMY
    }

    def time_range(self, s):
        return None, None

    @classmethod
    def singletons(cls, s):
        from .. import StatisticName
        source = s.query(Dummy).one()
        name = s.query(StatisticName).filter(StatisticName.owner == source).one()
        return source, name


class CompositeComponent(Base):

    __tablename__ = 'composite_component'

    id = Column(Integer, primary_key=True)
    input_source_id = Column(Integer, ForeignKey('source.id', ondelete='cascade'), nullable=False)
    input_source = relationship('Source', foreign_keys=[input_source_id])
    output_source_id = Column(Integer, ForeignKey('composite_source.id', ondelete='cascade'), nullable=False)
    output_source = relationship('Composite', foreign_keys=[output_source_id])
    UniqueConstraint(output_source_id, input_source_id)  # ordered so output is a useful index


class Composite(Source):

    __tablename__ = 'composite_source'

    id = Column(Integer, ForeignKey('source.id', ondelete='cascade'), primary_key=True)
    components = relationship('Source', secondary='composite_component')
    n_components = Column(Integer, nullable=False)

    __mapper_args__ = {
        'polymorphic_identity': SourceType.COMPOSITE
    }

    def time_range(self, s):
        return None, None

    @classmethod
    def clean(cls, s):
        # see test_recursive
        q_input_counts = s.query(Composite.id,
                                 count(CompositeComponent.input_source_id).label('count')). \
            outerjoin(CompositeComponent, CompositeComponent.output_source_id == Composite.id). \
            group_by(Composite.id).cte()

        q_bad_nodes = s.query(Composite.id). \
            join(q_input_counts, q_input_counts.c.id == Composite.id). \
            filter(Composite.n_components != q_input_counts.c.count)

        if s.query(count(Composite.id)).filter(Composite.id.in_(q_bad_nodes)).scalar():
            log.warning('Need to clean expired composite sources (may take some time)')
            q_bad_nodes = q_bad_nodes.cte(recursive=True)
            q_all_nodes = q_bad_nodes. \
                union_all(s.query(Composite.id).
                          join(CompositeComponent,
                               CompositeComponent.output_source_id == Composite.id).
                          join(q_bad_nodes,
                               CompositeComponent.input_source_id == q_bad_nodes.c.id)).select()
            log.debug(f'Executing {q_all_nodes}')
            s.flush()
            with timing('GC of composite sources'):
                s.query(Source).filter(Source.id.in_(q_all_nodes)).delete(synchronize_session=False)

    @classmethod
    def find(cls, s, *sources):
        from ...data.frame import _tables
        ids = [source.id if isinstance(source, Source) else source for source in sources]
        t = _tables()
        q = s.query(Composite)
        for id in ids:
            component = t.cc.alias()
            q = q.join(component, Composite.id == component.c.output_source_id).\
                filter(component.c.input_source_id == id)
        return q.one_or_none()

    @classmethod
    def create(cls, s, *sources):
        composite = add(s, Composite(n_components=0))
        for source in sources:
            add(s, CompositeComponent(input_source=source, output_source=composite))
            composite.n_components += 1
        return composite
