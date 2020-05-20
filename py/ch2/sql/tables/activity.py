
import datetime as dt
from logging import getLogger

from sqlalchemy import Column, Text, Integer, ForeignKey, UniqueConstraint, desc
from sqlalchemy.orm import relationship, backref

from .source import Source, SourceType, GroupedSource
from ..support import Base
from ..types import Time, Sort, ShortCls, NullText, Name, name_and_title, simple_name
from ...lib.date import format_time, local_date_to_time, local_time_to_time
from ...names import Titles

log = getLogger(__name__)


class ActivityGroup(Base):

    __tablename__ = 'activity_group'

    id = Column(Integer, primary_key=True)
    name = Column(Name, nullable=False, index=True)
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=False, server_default='')
    sort = Column(Sort, nullable=False)

    def __init__(self, **kargs):
        super().__init__(**name_and_title(kargs))

    def __str__(self):
        return self.name

    @classmethod
    def from_name(cls, s, name):
        if not name:
            return None
        elif isinstance(name, ActivityGroup):
            return name  # allow callers to already have an instance
        else:
            return s.query(ActivityGroup).filter(ActivityGroup.name.ilike(name)).one()


class ActivityJournal(GroupedSource):

    __tablename__ = 'activity_journal'

    id = Column(Integer, ForeignKey('source.id', ondelete='cascade'), primary_key=True)
    file_hash_id = Column(Integer, ForeignKey('file_hash.id'), nullable=False)
    file_hash = relationship('FileHash', backref=backref('activity_journal', uselist=False))
    start = Column(Time, nullable=False)
    finish = Column(Time, nullable=False)
    UniqueConstraint(start)
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
    def at(cls, s, local_time_or_date, activity_group=None):
        try:
            activity_journal = cls.at_local_time(s, local_time_or_date, activity_group=activity_group)
        except:
            activity_journal = cls.at_date(s, local_time_or_date, activity_group=activity_group)
        if activity_group and activity_journal.activity_group != ActivityGroup.from_name(s, activity_group):
            raise Exception(f'Activity journal from {local_time_or_date} '
                            f'does not match activity group {activity_group}')
        log.debug(f'Resolved {local_time_or_date} / {activity_group} to {activity_journal}')
        return activity_journal

    @classmethod
    def at_date(cls, s, date, activity_group=None):
        day = local_date_to_time(date)
        journals = s.query(ActivityJournal).filter(ActivityJournal.start >= day,
                                                   ActivityJournal.start < day + dt.timedelta(days=1)).all()
        if activity_group:
            activity_group = ActivityGroup.from_name(s, activity_group)
            journals = [journal for journal in journals if journal.activity_group == activity_group]
        if not journals:
            raise Exception(f'No activity journal found at {date} for activity group {activity_group}')
        elif len(journals) > 1:
            raise Exception(f'Multiple activity journals found at {date} for activity group {activity_group}')
        else:
            return journals[0]

    @classmethod
    def at_local_time(cls, s, local_time, activity_group=None):
        time = local_time_to_time(local_time)
        q = s.query(ActivityJournal).filter(ActivityJournal.start == time)
        if activity_group:
            activity_group = ActivityGroup.from_name(s, activity_group)
            q = q.filter(ActivityJournal.activity_group_id == activity_group.id)
        return q.one()

    @classmethod
    def before_local_time(cls, s, local_time):
        time = local_time_to_time(local_time)
        return s.query(ActivityJournal). \
            filter(ActivityJournal.start < time). \
            order_by(desc(ActivityJournal.start)). \
            limit(1).one_or_none()

    @classmethod
    def after_local_time(cls, s, local_time):
        time = local_time_to_time(local_time)
        return s.query(ActivityJournal). \
            filter(ActivityJournal.start >= (time + dt.timedelta(days=1))). \
            order_by(ActivityJournal.start). \
            limit(1).one_or_none()

    @classmethod
    def number_of_activities(cls, s):
        return s.query(ActivityJournal).count()

    def __lt__(self, other):
        # allows sorting in displays
        if isinstance(other, ActivityJournal):
            return self.start < other.start
        else:
            return False


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
    constraint = Column(NullText, index=True)
    UniqueConstraint(activity_journal_id, start, finish, owner, constraint)

    def __str__(self):
        return 'ActivityBookmark from %s - %s' % (format_time(self.start), format_time(self.finish))

