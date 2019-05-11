
import datetime as dt

from sqlalchemy import Column, Text, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship, backref

from .source import Source, SourceType
from ..support import Base
from ..types import Time, Sort, ShortCls, Str, NullStr
from ...lib.date import format_time, local_date_to_time


class ActivityGroup(Base):

    __tablename__ = 'activity_group'

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False, server_default='')
    description = Column(Text, nullable=False, server_default='')
    sort = Column(Sort, nullable=False, server_default='')

    def __str__(self):
        return 'ActivityGroup "%s"' % self.name


class ActivityJournal(Source):

    __tablename__ = 'activity_journal'

    id = Column(Integer, ForeignKey('source.id', ondelete='cascade'), primary_key=True)
    activity_group_id = Column(Integer, ForeignKey('activity_group.id'), nullable=False)
    activity_group = relationship('ActivityGroup')
    name = Column(Text, unique=True)
    fit_file = Column(Text, nullable=False, unique=True)
    start = Column(Time, nullable=False,)
    finish = Column(Time, nullable=False)
    UniqueConstraint(activity_group_id, start)

    __mapper_args__ = {
        'polymorphic_identity': SourceType.ACTIVITY
    }

    def __str__(self):
        return 'ActivityJournal %s %s to %s' % (self.activity_group.name,
                                                format_time(self.start), format_time(self.finish))

    def time_range(self, s):
        return self.start, self.finish

    @classmethod
    def at_date(cls, s, date):
        day = local_date_to_time(date)
        return s.query(ActivityJournal).filter(ActivityJournal.start >= day,
                                               ActivityJournal.start < day + dt.timedelta(days=1)).all()

    @classmethod
    def from_id(cls, s, id):
        return s.query(ActivityJournal).filter(ActivityJournal.id == id).one()


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
