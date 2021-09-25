import datetime as dt
from abc import abstractmethod
from enum import IntEnum
from logging import getLogger
from operator import or_

from sqlalchemy import ForeignKey, Column, Integer, func, UniqueConstraint, Boolean, Date
from sqlalchemy.event import listens_for
from sqlalchemy.orm import Session, relationship
from sqlalchemy.sql.functions import count

from ..support import Base
from ..triggers import add_child_ddl
from ..types import OpenSched, ShortCls, short_cls
from ..utils import add
from ...common.date import time_to_local_date, max_time, min_time, extend_range
from ...common.names import UNDEF, TIME_ZERO
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
    ITEM = 8
    MODEL = 9
    ACTIVITY_TOPIC = 10
    SECTOR = 11


class Source(Base):

    __tablename__ = 'source'

    id = Column(Integer, primary_key=True)
    type = Column(Integer, nullable=False, index=True)  # index needed for fast deletes of subtypes
    activity_group_id = Column(Integer, ForeignKey('activity_group.id', ondelete='cascade'), nullable=True)
    activity_group = relationship('ActivityGroup')

    __mapper_args__ = {
        'polymorphic_identity': SourceType.SOURCE,
        'polymorphic_on': type
    }

    @abstractmethod
    def time_range(self, s):
        raise NotImplementedError('time_range for %s' % self)

    @classmethod
    def before_flush(cls, s):
        cls.__record_dirty_intervals(s)

    @classmethod
    def __record_dirty_intervals(cls, s):
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
            if isinstance(instance, StatisticJournal):
                if s.is_modified(instance) and instance.time and not isinstance(instance, StatisticJournalText):
                    start, finish = extend_range(start, finish, instance.time)
                elif instance.statistic_name is None or instance.source is None:
                    log.warning(f'Loading with incomplete name/source data (bad dirty logic) '
                                f'(statistic_name_id {instance.statistic_name_id})')
        # all new statistics that aren't associated with intervals and have non-null data
        # (avoid triggering on empty diary entries)
        for instance in s.new:
            # ignore constants as time 0
            # ignore textual values
            if isinstance(instance, StatisticJournal):
                if not isinstance(instance.source, Interval) and not isinstance(instance.source, StatisticJournalText):
                    start, finish = extend_range(start, finish, instance.time)
                elif instance.statistic_name is None or instance.source is None:
                    log.warning(f'Loading with incomplete name/source data (bad dirty logic) '
                                f'(statistic_name_id {instance.statistic_name_id})')
        if start is not None:
            Interval.record_dirty_times(s, start, finish)

    @classmethod
    def from_id(cls, s, id):
        return s.query(Source).filter(Source.id == id).one()

    def long_str(self):
        return str(self)

    def get_qname(self, s, qname, limit=True):
        from .. import StatisticJournal, StatisticName, ActivityGroup
        owner, name, group = StatisticName.parse(qname, default_activity_group=UNDEF)
        q = s.query(StatisticJournal). \
            join(StatisticName). \
            filter(StatisticName.name.ilike(name),
                   StatisticJournal.source_id == self.id)
        if owner:
            q = q.filter(StatisticName.owner == owner)
        if group is not UNDEF:
            q = q.join(ActivityGroup).filter(ActivityGroup.name == group)
        if limit:
            q = q.filter(or_(StatisticJournal.serial.is_(None), StatisticJournal.serial == 0))
        log.debug(q)
        with timing(f'get_qname {self.id} {owner} {name} {group}'):
            return q.all()



@listens_for(Session, 'before_flush')
def before_flush(session, context, instances):
    Source.before_flush(session)


class GroupedSource(Source):

    __abstract__ = True

    def __init__(self, **kargs):
        if 'activity_group' not in kargs: raise Exception(f'{self.__class__.__name__} requires activity group')
        super().__init__(**kargs)

    def long_str(self):
        return super().long_str() + f' ({self.activity_group.name})'


class UngroupedSource(Source):

    __abstract__ = True

    def __init__(self, **kargs):
        if 'activity_group' in kargs: raise Exception(f'{self.__class__.__name__} has no activity group')
        super().__init__(**kargs)


class NoStatistics(Exception):
    pass


@add_child_ddl(Source)
class Interval(Source):

    __tablename__ = 'interval'

    id = Column(Integer, ForeignKey('source.id', ondelete='cascade'), primary_key=True)
    schedule = Column(OpenSched, nullable=False, index=True)
    owner = Column(ShortCls, nullable=False)
    dirty = Column(Boolean, default=False, nullable=False)
    permanent = Column(Boolean, default=False, nullable=False)  # if true, do not clean when dirty
    # these are for the schedule - finish is redundant (start is not because of timezone issues)
    start = Column(Date, nullable=False, index=True)
    finish = Column(Date, nullable=False, index=True)

    __mapper_args__ = {
        'polymorphic_identity': SourceType.INTERVAL
    }

    def __init__(self, start=None, finish=None, schedule=None, **kargs):
        if not start: raise ValueError('Missing start')
        if not schedule: raise ValueError('Missing schedule')
        if not finish: finish = schedule.next_frame(start)
        super().__init__(start=start, finish=finish, schedule=schedule, **kargs)

    def __str__(self):
        owner = self.owner if isinstance(self.owner, str) else short_cls(self.owner)
        return 'Interval "%s from %s" (owner %s)' % (self.schedule, self.start, owner)

    @classmethod
    def _raw_statistics_time_range(cls, s, exclude_owners=None):
        '''
        The time range over which statistics exist, ignoring constants at "time zero".
        This is the first to the last time for any statistics - it pays no attention to gaps.
        '''
        from .statistic import StatisticJournal, StatisticName
        # exclude 2 days from zero because here are some stats set at the date equivalent to zero time,
        # but because of date/time conversions and timezones these are not exactly as time zero
        q = s.query(func.min(StatisticJournal.time), func.max(StatisticJournal.time)). \
            filter(StatisticJournal.time > TIME_ZERO + dt.timedelta(days=2))
        if exclude_owners:
            q = q.join(StatisticName).filter(~StatisticName.owner.in_(exclude_owners))
        start, finish = q.one()
        if start and finish:
            return start, finish
        else:
            raise NoStatistics('No statistics are currently defined')

    @classmethod
    def missing_starts(cls, s, expected, schedule, interval_owner, exclude_owners=None):
        '''
        Previous approach was way too complicated and not thread-safe.  Instead, just enumerate intervals and test.
        '''
        try:
            stats_start_time, stats_finish_time = cls._raw_statistics_time_range(s, exclude_owners=exclude_owners)
            start = time_to_local_date(stats_start_time)
            finish = time_to_local_date(stats_finish_time)
            log.debug('Statistics (in general) exist %s - %s' % (start, finish))
            start = schedule.start_of_frame(start)
            finish = schedule.next_frame(finish)
            while start < finish:
                existing = s.query(Interval). \
                    filter(Interval.start == start,
                           Interval.schedule == schedule,
                           Interval.owner == interval_owner).count()
                if existing != expected:
                    yield start
                start = schedule.next_frame(start)
        except NoStatistics:
            log.warning('No data available')

    @classmethod
    def dirty_all(cls, s):
        log.warning('Dirtying all Intervals')
        s.record_dirty_intervals(interval.id for interval in s.query(Interval).all())

    @classmethod
    def record_dirty_times(cls, s, start, finish):
        '''
        Record dirty intervals that include data in the given TIME range,
        '''
        start, finish = time_to_local_date(start), time_to_local_date(finish)
        q = s.query(Interval.id).filter(Interval.start <= finish, Interval.finish > start)
        # do not mark in-place because we can get deadlock transactions.
        # instead, save in session and update at end of transaction
        s.record_dirty_intervals(row[0] for row in q.all())

    @classmethod
    def clean(cls, s, owner=None):
        q = s.query(Interval.id).filter(Interval.dirty == True)
        if owner:
            extra = f' (owner {owner})'
            q = q.filter(Interval.owner == owner)
        else:
            extra = ' (not permanent)'
            q = q.filter(Interval.permanent == False)
        count = q.count()
        if count:
            log.debug(f'Cleaning {count} dirty intervals {extra}')
            s.query(Source).filter(Source.id.in_(q)).delete(synchronize_session=False)
            s.commit()
        log.debug('Intervals clean')


class CompositeComponent(Base):

    __tablename__ = 'composite_component'

    id = Column(Integer, primary_key=True)
    input_source_id = Column(Integer, ForeignKey('source.id', ondelete='cascade'),
                             nullable=False, index=True)
    input_source = relationship('Source', foreign_keys=[input_source_id])
    output_source_id = Column(Integer, ForeignKey('composite_source.id', ondelete='cascade'),
                              nullable=False)  # no need for index - see unique below
    output_source = relationship('Composite', foreign_keys=[output_source_id])
    UniqueConstraint(output_source_id, input_source_id)  # ordered so output is a useful index


@add_child_ddl(Source)
class Composite(Source):

    __tablename__ = 'composite_source'

    id = Column(Integer, ForeignKey('source.id', ondelete='cascade'), primary_key=True)
    # viewonly below was in response to:
    # home/andrew/project/choochoo/py/env/lib/python3.9/site-packages/SQLAlchemy-1.4.0b1-py3.9-linux-x86_64.egg/sqlalchemy/orm/relationships.py:3428: SAWarning: relationship 'Composite.components' will copy column composite_source.id to column composite_component.output_source_id, which conflicts with relationship(s): 'CompositeComponent.output_source' (copies composite_source.id to composite_component.output_source_id). If this is not the intention, consider if these relationships should be linked with back_populates, or if viewonly=True should be applied to one or more if they are read-only. For the less common case that foreign key constraints are partially overlapping, the orm.foreign() annotation can be used to isolate the columns that should be written towards.   The 'overlaps' parameter may be used to remove this warning.
    # /home/andrew/project/choochoo/py/env/lib/python3.9/site-packages/SQLAlchemy-1.4.0b1-py3.9-linux-x86_64.egg/sqlalchemy/orm/relationships.py:3428: SAWarning: relationship 'Composite.components' will copy column source.id to column composite_component.input_source_id, which conflicts with relationship(s): 'CompositeComponent.input_source' (copies source.id to composite_component.input_source_id). If this is not the intention, consider if these relationships should be linked with back_populates, or if viewonly=True should be applied to one or more if they are read-only. For the less common case that foreign key constraints are partially overlapping, the orm.foreign() annotation can be used to isolate the columns that should be written towards.   The 'overlaps' parameter may be used to remove this warning.
    components = relationship('Source', secondary='composite_component', viewonly=True)
    n_components = Column(Integer, nullable=False)

    __mapper_args__ = {
        'polymorphic_identity': SourceType.COMPOSITE
    }

    def time_range(self, s):
        return None, None

    @classmethod
    def clean(cls, s):
        log.debug('Searching for invalid composites')
        # see test_recursive
        q_input_counts = s.query(Composite.id,
                                 count(CompositeComponent.input_source_id).label('count')). \
            outerjoin(CompositeComponent, CompositeComponent.output_source_id == Composite.id). \
            group_by(Composite.id).cte()
        q_bad_nodes = s.query(Composite.id). \
            join(q_input_counts, q_input_counts.c.id == Composite.id). \
            filter(Composite.n_components != q_input_counts.c.count)
        q_count = s.query(count(Composite.id)).filter(Composite.id.in_(q_bad_nodes))
        # log.debug(q_count)
        if q_count.scalar():
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
    def create(cls, s, sources):
        composite = add(s, Composite(n_components=0))
        for source in sources:
            if isinstance(source, int):
                add(s, CompositeComponent(input_source_id=source, output_source=composite))
            else:
                add(s, CompositeComponent(input_source=source, output_source=composite))
            composite.n_components += 1
        return composite

    def long_str(self):
        interesting = [component for component in self.components if not isinstance(component, Composite)]
        msg = f'Composite (id {self.id}, {self.n_components} comp)'
        if self.activity_group: msg += f' ({self.activity_group.name})'
        if interesting:
            msg += ' [' + ', '.join(source.long_str() for source in interesting) + ']'
        return msg
