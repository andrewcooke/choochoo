import datetime as dt
from enum import IntEnum
from logging import getLogger
from random import choice
from string import ascii_letters

import pytz
from sqlalchemy import create_engine, Integer, Column, union, select, not_, ForeignKey, UniqueConstraint, Text, \
    TypeDecorator, DateTime, Index
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, backref

from ch2 import upload, BASE
from ch2.commands.args import V, bootstrap_db, DEV, UPLOAD, TEXT
from ch2.commands.search import do_search
from ch2.common.args import m, mm
from ch2.config.profiles.acooke import acooke
from tests import LogTestCase, random_test_user, TempDirOnSuccess

log = getLogger(__name__)


class TestSearch(LogTestCase):

    def test_search(self):

        user = random_test_user()
        with TempDirOnSuccess() as f:
            config = bootstrap_db(user, mm(BASE), f, m(V), '5', configurator=acooke)

            with self.assertRaisesRegex(Exception, 'could not be validated'):
                do_search(config.db, ['active-distance > 100'])

            config = bootstrap_db(user, mm(BASE), f, m(V), '5', mm(DEV), UPLOAD,
                                  'data/test/source/personal/2018-03-04-qdp.fit')
            upload(config)
            self.assertTrue(do_search(config.db, ['active-distance > 100']))
            self.assertTrue(do_search(config.db, ['2018-03-04T07:16:33'], cmd=TEXT))
            self.assertTrue(do_search(config.db, ['start > 2018-03-01']))
            self.assertFalse(do_search(config.db, ['start < 2018-03-01']))


class SQLAlchemyTest1(LogTestCase):

    def test_sqlalchemy(self):

        engine = create_engine('sqlite:///:memory:')
        Base = declarative_base()
        Session = sessionmaker(engine)

        class Table(Base):
            __tablename__ = 'table'
            id = Column(Integer, primary_key=True)

        Base.metadata.create_all(engine)

        with Session() as s:
            q1 = select(Table).filter(Table.id == 1)
            q2 = select(Table).filter(Table.id == 2)
            q3 = union(q1, q2).subquery()

        with Session() as s:
            q1 = select(Table).filter(Table.id == 1)
            q2 = select(Table).filter(Table.id == 2)
            cte = union(q1, q2).cte()
            q3 = select(Table).filter(Table.id.in_(cte))
            q4 = select(Table).filter(Table.id.in_(cte))
            q5 = union(q3, q4).subquery()
            log.debug(q5)


class SQLAlchemyTest2(LogTestCase):

    def test_sqlalchemy(self):

        # using postgres with log_statement=all so that we can see the incorrect queries
        # (use a transient docker instance)

        dbname = ''.join(choice(ascii_letters) for _ in range(16)).lower()
        # https://stackoverflow.com/questions/6506578/how-to-create-a-new-database-using-sqlalchemy
        engine = create_engine('postgresql://postgres@localhost:5432/postgres')
        conn = engine.connect()
        conn.execute('commit')
        conn.execute(f'create database {dbname}')
        conn.close()

        engine = create_engine(f'postgresql://postgres@localhost:5432/{dbname}')
        Base = declarative_base()
        Session = sessionmaker(engine)

        AND, OR, NULL = 'and', 'or', 'null'
        UNDEF = object()

        class SourceType(IntEnum):
            SOURCE = 0
            ACTIVITY = 2
            ACTIVITY_TOPIC = 10

        class StatisticJournalType(IntEnum):
            STATISTIC = 0
            TIMESTAMP = 4

        class UTC(TypeDecorator):
            impl = DateTime(timezone=True)
            def process_result_value(self, value, dialect):
                if value is None:
                    return None
                return value.replace(tzinfo=pytz.UTC)

        class FileHash(Base):
            __tablename__ = 'file_hash'
            id = Column(Integer, primary_key=True)
            hash = Column(Text, nullable=False, index=True, unique=True)

        class Source(Base):
            __tablename__ = 'source'
            id = Column(Integer, primary_key=True)
            type = Column(Integer, nullable=False, index=True)
            __mapper_args__ = {
                'polymorphic_identity': SourceType.SOURCE,
                'polymorphic_on': type
            }

        class GroupedSource(Source):
            __abstract__ = True

        class ActivityJournal(GroupedSource):
            __tablename__ = 'activity_journal'
            id = Column(Integer, ForeignKey('source.id', ondelete='cascade'), primary_key=True)
            file_hash_id = Column(Integer, ForeignKey('file_hash.id'), nullable=False, index=True, unique=True)
            file_hash = relationship('FileHash', backref=backref('activity_journal', uselist=False))
            start = Column(UTC, nullable=False, index=True, unique=True)
            finish = Column(UTC, nullable=False)
            utm_srid = Column(Integer)
            __mapper_args__ = {
                'polymorphic_identity': SourceType.ACTIVITY
            }

        class ActivityTopicJournal(GroupedSource):
            __tablename__ = 'activity_topic_journal'
            id = Column(Integer, ForeignKey('source.id', ondelete='cascade'), primary_key=True)
            file_hash_id = Column(Integer, ForeignKey('file_hash.id'),
                                  nullable=False, index=True, unique=True)
            file_hash = relationship('FileHash', backref=backref('activity_topic_journal', uselist=False))
            __mapper_args__ = {
                'polymorphic_identity': SourceType.ACTIVITY_TOPIC
            }

        class StatisticName(Base):
            # some column types modified for test
            __tablename__ = 'statistic_name'
            id = Column(Integer, primary_key=True)
            name = Column(Text, nullable=False)
            title = Column(Text, nullable=False)
            description = Column(Text)
            units = Column(Text)
            summary = Column(Text)
            owner = Column(Text, nullable=False, index=True)
            statistic_journal_type = Column(Integer, nullable=False)
            UniqueConstraint(name, owner)

        class StatisticJournal(Base):
            __tablename__ = 'statistic_journal'
            id = Column(Integer, primary_key=True)
            type = Column(Integer, nullable=False, index=True)
            statistic_name_id = Column(Integer, ForeignKey('statistic_name.id', ondelete='cascade'), nullable=False)
            statistic_name = relationship('StatisticName')
            source_id = Column(Integer, ForeignKey('source.id', ondelete='cascade'), nullable=False)
            source = relationship('Source')
            time = Column(UTC, nullable=False, index=True)
            serial = Column(Integer)
            UniqueConstraint(statistic_name_id, time, source_id)
            UniqueConstraint(statistic_name_id, source_id, serial)
            Index('from_activity_timespan', source_id, statistic_name_id, time)
            __mapper_args__ = {
                'polymorphic_identity': StatisticJournalType.STATISTIC,
                'polymorphic_on': 'type'
            }

        class StatisticJournalTimestamp(StatisticJournal):
            __tablename__ = 'statistic_journal_timestamp'
            id = Column(Integer, ForeignKey('statistic_journal.id', ondelete='cascade'), primary_key=True)
            value = Column(UTC, nullable=False)
            __mapper_args__ = {
                'polymorphic_identity': StatisticJournalType.TIMESTAMP
            }

        Base.metadata.create_all(engine)

        def build_source_query(s, value):
            q = s.query(Source.id). \
                join(StatisticJournalTimestamp). \
                join(StatisticName). \
                filter(StatisticName.name.like('start')). \
                filter(StatisticJournalTimestamp.value > value)
            q_direct = s.query(ActivityJournal.id). \
                filter(ActivityJournal.id.in_(q.subquery()))
            q_via_topic = s.query(ActivityJournal.id). \
                join(FileHash). \
                join(ActivityTopicJournal). \
                filter(ActivityTopicJournal.id.in_(q.subquery()))
            constraints = union(q_direct, q_via_topic).subquery().select()
            return s.query(Source).filter(Source.id.in_(constraints))

        with Session() as s:
            build_source_query(s, dt.datetime(2020, 1, 1, 3, 0, tzinfo=pytz.UTC)).all()
            build_source_query(s, dt.datetime(2021, 1, 1, 3, 0, tzinfo=pytz.UTC)).all()
