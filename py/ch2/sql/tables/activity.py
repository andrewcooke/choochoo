
import datetime as dt
from logging import getLogger

from geoalchemy2 import Geography, Geometry
from sqlalchemy import Column, Text, Integer, ForeignKey, UniqueConstraint, desc, DateTime, Index, text
from sqlalchemy.orm import relationship, backref

from .source import SourceType, GroupedSource, Source
from ..support import Base
from ..triggers import add_child_ddl, add_text
from ..types import Sort, ShortCls, NullText, Name, name_and_title, Point, UTC
from ..utils import WGS84_SRID
from ...common.date import format_time, local_date_to_time, local_time_to_time
from ...lib.utils import timing

log = getLogger(__name__)


class ActivityGroup(Base):

    __tablename__ = 'activity_group'

    id = Column(Integer, primary_key=True)
    name = Column(Name, nullable=False, index=True, unique=True)
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=False, server_default='')
    sort = Column(Sort, nullable=False)

    def __init__(self, **kargs):
        super().__init__(**name_and_title(kargs))

    def __str__(self):
        return self.name

    @classmethod
    def from_name(cls, s, name, none=False):
        if not name:
            return None
        elif isinstance(name, ActivityGroup):
            return name  # allow callers to already have an instance
        else:
            instance = s.query(ActivityGroup).filter(ActivityGroup.name.ilike(name)).one_or_none()
            if instance is None and not none:
                raise Exception(f'No activity group defined for {name}')
            return instance


@add_child_ddl(Source)
@add_text('''
alter table %(table)s
  add constraint no_activity_overlap
  exclude using gist (tstzrange(start, finish) with &&);
''')
class ActivityJournal(GroupedSource):

    __tablename__ = 'activity_journal'

    id = Column(Integer, ForeignKey('source.id', ondelete='cascade'), primary_key=True)
    file_hash_id = Column(Integer, ForeignKey('file_hash.id'), nullable=False, index=True, unique=True)
    file_hash = relationship('FileHash', backref=backref('activity_journal', uselist=False))
    start = Column(UTC, nullable=False, index=True, unique=True)
    finish = Column(UTC, nullable=False)
    # nullable because created later
    centre = Column(Geography('Point', srid=WGS84_SRID))
    utm_srid = Column(Integer)
    # used to detect folding back
    route_a = Column(Geography('LineStringM', srid=WGS84_SRID))  # azimuth
    # used to calculate valuses from offsets
    route_d = Column(Geography('LineStringM', srid=WGS84_SRID))  # distance
    route_et = Column(Geography('LineStringZM', srid=WGS84_SRID))  # time
    # used to detect climbs
    route_edt = Column(Geography('LineStringZM', srid=WGS84_SRID))  # elevation, distance / m * 1e7 + elapsed time

    __mapper_args__ = {
        'polymorphic_identity': SourceType.ACTIVITY
    }

    def __str__(self):
        return 'ActivityJournal %s %s to %s' % (self.activity_group.name,
                                                format_time(self.start), format_time(self.finish))

    def time_range(self, s):
        return self.start, self.finish

    def get_all_qname(self, s, qname, limit=True):
        direct = self.get_qname(s, qname, limit=limit)
        indirect = self.get_activity_topic_journal(s).get_qname(s, qname, limit=limit)
        log.debug(f'{len(direct)} {len(indirect)}')
        return direct + indirect

    def get_activity_topic_journal(self, s):
        from .. import ActivityTopicJournal, FileHash
        with timing('get_activity_topic_journal'):
            return s.query(ActivityTopicJournal). \
                join(FileHash). \
                join(ActivityJournal). \
                filter(ActivityJournal.id == self.id).one()

    @classmethod
    def at(cls, s, local_time_or_date, activity_group=None):
        try:
            activity_journal = cls.at_local_time(s, local_time_or_date, activity_group=activity_group)
        except ValueError:
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
        if q.count():
            return q.one()
        else:
            msg = f'No activity found at {local_time} ({time})'
            if activity_group: msg += f' for {activity_group}'
            raise Exception(msg)

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
    start = Column(UTC, nullable=False)
    finish = Column(UTC, nullable=False)
    UniqueConstraint(activity_journal_id, start)

    def __str__(self):
        return 'ActivityTimespan from %s - %s' % (format_time(self.start), format_time(self.finish))


class ActivityBookmark(Base):

    __tablename__ = 'activity_bookmark'

    id = Column(Integer, primary_key=True)
    activity_journal_id = Column(Integer, ForeignKey('source.id', ondelete='cascade'), nullable=False)
    activity_journal = relationship('ActivityJournal')
    start = Column(UTC, nullable=False)
    finish = Column(UTC, nullable=False)
    owner = Column(ShortCls, nullable=False, index=True)  # index for deletion
    constraint = Column(NullText, index=True)
    UniqueConstraint(activity_journal_id, start, finish, owner, constraint)

    def __str__(self):
        return 'ActivityBookmark from %s - %s' % (format_time(self.start), format_time(self.finish))

