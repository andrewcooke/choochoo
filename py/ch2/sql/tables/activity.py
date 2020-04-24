
import datetime as dt
from logging import getLogger

from sqlalchemy import Column, Text, Integer, ForeignKey, UniqueConstraint, desc
from sqlalchemy.orm import relationship, backref

from .source import Source, SourceType
from ..support import Base
from ..types import Time, Sort, ShortCls, NullStr
from ...lib.date import format_time, local_date_to_time, local_time_to_time

log = getLogger(__name__)


class ActivityGroup(Base):

    __tablename__ = 'activity_group'

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False, server_default='')
    description = Column(Text, nullable=False, server_default='')
    sort = Column(Sort, nullable=False, server_default='')

    def __str__(self):
        return self.name

    @classmethod
    def from_name(cls, s, name):
        if not name:
            raise Exception('Missing activity group (None)')
        if isinstance(name, ActivityGroup):
            return name  # allow callers to already have an instance
        else:
            return s.query(ActivityGroup).filter(ActivityGroup.name.ilike(name)).one()


class ActivityJournal(Source):

    __tablename__ = 'activity_journal'

    id = Column(Integer, ForeignKey('source.id', ondelete='cascade'), primary_key=True)
    activity_group_id = Column(Integer, ForeignKey('activity_group.id', ondelete='cascade'), nullable=False)
    activity_group = relationship('ActivityGroup')
    file_hash_id = Column(Integer, ForeignKey('file_hash.id'), nullable=False)
    file_hash = relationship('FileHash', backref=backref('activity_journal', uselist=False))
    start = Column(Time, nullable=False)
    finish = Column(Time, nullable=False)
    UniqueConstraint(activity_group_id, start)
    UniqueConstraint(file_hash_id)

    __mapper_args__ = {
        'polymorphic_identity': SourceType.ACTIVITY
    }

    def __str__(self):
        return 'ActivityJournal %s %s to %s' % (self.activity_group.name,
                                                format_time(self.start), format_time(self.finish))

    def time_range(self, s):
        return self.start, self.finish

    def get_named(self, s, qname, owner=None):
        from .. import StatisticJournal, StatisticName
        from ...data.constraint import parse_qname
        name, group = parse_qname(qname)
        q = s.query(StatisticJournal). \
            join(ActivityJournal). \
            join(StatisticName). \
            filter(StatisticName.name.ilike(name),
                   StatisticJournal.source_id == self.id)
        if owner: q = q.filter(StatisticName.owner == owner)
        if group: q = q.join(ActivityGroup).filter(ActivityGroup.name.ilike(group))
        elif group is None: q = q.join(ActivityGroup).filter(ActivityGroup.id == ActivityJournal.activity_group_id)
        return q.all()

    def get_all_named(self, s, qname, owner=None):
        return self.get_named(s, qname, owner=owner) + \
               self.get_activity_topic_journal(s).get_named(s, qname, owner=owner)

    def get_activity_topic_journal(self, s):
        from .. import ActivityTopicJournal, FileHash
        return s.query(ActivityTopicJournal). \
            join(FileHash). \
            join(ActivityJournal). \
            filter(ActivityJournal.id == self.id).one()

    @classmethod
    def at_date(cls, s, date):
        day = local_date_to_time(date)
        return s.query(ActivityJournal).filter(ActivityJournal.start >= day,
                                               ActivityJournal.start < day + dt.timedelta(days=1)).all()

    @classmethod
    def at_local_time(cls, s, local_time):
        time = local_time_to_time(local_time)
        return s.query(ActivityJournal).filter(ActivityJournal.start == time).one()

    @classmethod
    def before_local_time(cls, s, local_time):
        time = local_date_to_time(local_time)
        return s.query(ActivityJournal). \
            filter(ActivityJournal.start < time). \
            order_by(desc(ActivityJournal.start)). \
            limit(1).one_or_none()

    @classmethod
    def after_local_time(cls, s, local_time):
        time = local_date_to_time(local_time)
        return s.query(ActivityJournal). \
            filter(ActivityJournal.start >= (time + dt.timedelta(days=1))). \
            order_by(ActivityJournal.start). \
            limit(1).one_or_none()

    @classmethod
    def number_of_activities(cls, s):
        return s.query(ActivityJournal).count()


class ActivityTimespan(Base):

    __tablename__ = 'activity_timespan'

    id = Column(Integer, primary_key=True)
    activity_journal_id = Column(Integer, ForeignKey('source.id', ondelete='cascade'),
                                 nullable=False, index=True)
    activity_journal = relationship('ActivityJournal',
                                    backref=backref('timespans', cascade='all, delete-orphan',
                                                    passive_deletes=True,
                                                    order_by='ActivityTimespan.start'))
    start = Column(Time, nullable=False)
    finish = Column(Time, nullable=False)
    UniqueConstraint(activity_journal_id, start)

    def __str__(self):
        return 'ActivityTimespan from %s - %s' % (format_time(self.start), format_time(self.finish))


class ActivityBookmark(Base):

    __tablename__ = 'activity_bookmark'

    id = Column(Integer, primary_key=True)
    activity_journal_id = Column(Integer, ForeignKey('source.id', ondelete='cascade'), nullable=False)
    activity_journal = relationship('ActivityJournal')
    start = Column(Time, nullable=False)
    finish = Column(Time, nullable=False)
    owner = Column(ShortCls, nullable=False, index=True)  # index for deletion
    constraint = Column(NullStr, index=True)
    UniqueConstraint(activity_journal_id, start, finish, owner, constraint)

    def __str__(self):
        return 'ActivityBookmark from %s - %s' % (format_time(self.start), format_time(self.finish))

