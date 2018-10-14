
from enum import IntEnum

from sqlalchemy import ForeignKey, Column, Integer
from sqlalchemy.event import listens_for
from sqlalchemy.orm import Session

from ..support import Base
from ..types import Time, OpenSched
from ...lib.date import to_date, to_time
from ...lib.schedule import Schedule


class SourceType(IntEnum):

    SOURCE = 0
    INTERVAL = 1
    ACTIVITY = 2
    TOPIC = 3
    CONSTANT = 4


class Source(Base):

    __tablename__ = 'source'

    id = Column(Integer, primary_key=True)
    type = Column(Integer, nullable=False)
    time = Column(Time, nullable=False)

    __mapper_args__ = {
        'polymorphic_identity': SourceType.SOURCE,
        'polymorphic_on': type
    }

    @classmethod
    def before_flush(cls, session):
        cls.__clean_empty_diary(session)
        cls.__clean_dirty_intervals(session)

    @classmethod
    def __clean_empty_diary(cls, session):
        from .topic import TopicJournal
        from .statistic import StatisticJournal
        # if we have a journal entry that's new and associated with no new stats then remove it
        diary_cleanup = set()
        for instance in session.new:
            dirty = False
            if isinstance(instance, TopicJournal):
                for field in instance.topic.fields:
                    # todo - check for None explicitly once we can handle empty strings
                    if instance.statistics[field].value:
                        dirty = True
                        break
                if not dirty:
                    session.expunge(instance)
                    diary_cleanup.add(instance)
        if diary_cleanup:
            for instance in session.new:
                if isinstance(instance, StatisticJournal) and instance.source in diary_cleanup:
                    session.expunge(instance)

    @classmethod
    def __clean_dirty_intervals(cls, session):
        from ...stoats.calculate.summary import SummaryStatistics
        times = set()
        for always, instances in [(True, session.new), (False, session.dirty), (True, session.deleted)]:
            # wipe the containing intervals if this is a source that has changed in some way
            # and it's not an interval itself
            sources = [instance for instance in instances
                       if (isinstance(instance, Source) and
                           not isinstance(instance, Interval) and
                           instance.time is not None and
                           (always or session.is_modified(instance)))]
            times |= set(to_time(source.time) for source in sources)
        specs = [Schedule(spec) for spec in SummaryStatistics.pipeline_schedules(session)]
        for time in times:
            for spec in specs:
                start = spec.start_of_frame(time)
                interval = session.query(Interval). \
                    filter(Interval.time == start, Interval.schedule == spec).one_or_none()
                if interval:
                    session.delete(interval)


@listens_for(Session, 'before_flush')
def before_flush(session, context, instances):
    Source.before_flush(session)


class Interval(Source):

    __tablename__ = 'interval'

    id = Column(Integer, ForeignKey('source.id', ondelete='cascade'), primary_key=True)
    schedule = Column(OpenSched, nullable=False)
    # duplicates data for simplicity in processing
    # day after (exclusive date)
    finish = Column(Time, nullable=False)

    __mapper_args__ = {
        'polymorphic_identity': SourceType.INTERVAL
    }

    def __str__(self):
        return 'Interval "%s from %s"' % (self.schedule, to_date(self.time))
