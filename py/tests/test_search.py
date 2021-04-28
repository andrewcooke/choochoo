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
        WGS84_SRID = 4326

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

        class StatisticJournalType(IntEnum):
            STATISTIC = 0
            INTEGER = 1
            FLOAT = 2
            TEXT = 3
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
            # activity_group_id = Column(Integer, ForeignKey('activity_group.id', ondelete='cascade'), nullable=True)
            # activity_group = relationship('ActivityGroup')
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
            # centre = Column(Geography('Point', srid=WGS84_SRID))
            utm_srid = Column(Integer)
            # route_a = Column(Geography('LineStringM', srid=WGS84_SRID))  # delta azimuth
            # route_d = Column(Geography('LineStringM', srid=WGS84_SRID))  # distance
            # route_et = Column(Geography('LineStringZM', srid=WGS84_SRID))  # time
            # route_edt = Column(Geography('LineStringZM', srid=WGS84_SRID))  # elevation, distance / m * 1e7 + elapsed time
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
            @classmethod
            def parse(cls, qname, default_owner=None, default_activity_group=None):
                if ':' in qname:
                    left, group = qname.rsplit(':', 1)
                else:
                    left, group = qname, default_activity_group
                if '.' in left:
                    owner, name = left.rsplit('.', 1)
                else:
                    owner, name = default_owner, left
                log.debug(f'Parsed {qname} as {owner}.{name}:{group}')
                return owner, name, group

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

        STATISTIC_JOURNAL_CLASSES = {
            # StatisticJournalType.INTEGER: StatisticJournalInteger,
            # StatisticJournalType.FLOAT: StatisticJournalFloat,
            # StatisticJournalType.TEXT: StatisticJournalText,
            StatisticJournalType.TIMESTAMP: StatisticJournalTimestamp
        }
        Base.metadata.create_all(engine)

        def get_op_attr(op, value):
            attrs = {'=': '__eq__', '!=': '__ne__', '>': '__gt__', '>=': '__ge__', '<': '__lt__', '<=': '__le__'}
            if isinstance(value, str): attrs.update({'=': 'ilike', '!=': 'nlike'})
            return attrs[op]

        def get_source_ids(s, owner, name, op, value, group, type):
            op_attr = get_op_attr(op, value)
            statistic_journal = STATISTIC_JOURNAL_CLASSES[type]
            q = s.query(Source.id). \
                join(statistic_journal). \
                join(StatisticName). \
                filter(StatisticName.name.like(name))
            if owner:
                q = q.filter(StatisticName.owner.like(owner))
            if group is not UNDEF:
                raise Exception('not used in test')
            #     if group:
            #         q = q.join(ActivityGroup).filter(ActivityGroup.name.ilike(group))
            #     else:
            #         q = q.filter(Source.activity_group_id == None)
            if op_attr == 'nlike':
                q = q.filter(not_(statistic_journal.value.ilike(value)))
            else:
                q = q.filter(getattr(statistic_journal.value, op_attr)(value))
            return q

        def build_comparisons(s, ast, with_conversion):
            qname, op, value = ast
            owner, name, group = StatisticName.parse(qname, default_activity_group=UNDEF)
            if value is None:
                if op == '=':
                    raise Exception('not used in test')
                    # return get_source_ids_for_null(s, owner, name, group, with_conversion), True
                else:
                    return union(*[get_source_ids(s, owner, name, op, value, group, type)
                                   for type in StatisticJournalType
                                   if type != StatisticJournalType.STATISTIC]).subquery().select(), False
            elif isinstance(value, str):
                raise Exception('not used in test')
                # return get_source_ids(s, owner, name, op, value, group, StatisticJournalType.TEXT), False
            elif isinstance(value, dt.datetime):
                return get_source_ids(s, owner, name, op, value, group, StatisticJournalType.TIMESTAMP), False
            else:
                raise Exception('not used in test')
                # qint = get_source_ids(s, owner, name, op, value, group, StatisticJournalType.INTEGER)
                # qfloat = get_source_ids(s, owner, name, op, value, group, StatisticJournalType.FLOAT)
                # return union(qint, qfloat).subquery().select(), False

        def build_constraint(s, ast, attrs, with_conversion):
            qname, op, value = ast
            if qname in attrs:
                raise Exception('not used in test')
                # return build_property(s, ast), False
            else:
                return build_comparisons(s, ast, with_conversion)

        def build_constraints(s, ast, attrs, conversion=None):
            l, op, r = ast
            if op in (AND, OR):
                raise Exception('not used in test')
                # lcte = build_constraints(s, l, attrs, conversion=conversion)
                # rcte = build_constraints(s, r, attrs, conversion=conversion)
                # return build_join(op, lcte, rcte)
            else:
                constraint, null = build_constraint(s, ast, attrs, bool(conversion))
                if conversion: constraint = conversion(s, constraint, null)
                return constraint

        def build_source_query(s, ast, attrs, conversion=None):
            constraints = build_constraints(s, ast, attrs, conversion=conversion).cte()
            return s.query(Source).filter(Source.id.in_(constraints))

        def constrained_sources(s, ast, conversion=None):
            attrs = set()
            q = build_source_query(s, ast, attrs, conversion=conversion)
            return q.all()

        def activity_conversion(s, source_ids, null):
            q_direct = s.query(ActivityJournal.id). \
                filter(ActivityJournal.id.in_(source_ids.subquery()))
            q_via_topic = s.query(ActivityJournal.id). \
                join(FileHash). \
                join(ActivityTopicJournal). \
                filter(ActivityTopicJournal.id.in_(source_ids.subquery()))
            q = union(q_direct, q_via_topic).subquery().select()
            if null:
                return s.query(ActivityJournal.id).filter(not_(ActivityJournal.id.in_(q)))
            else:
                return q

        with Session() as s:
            constrained_sources(s, ('start', '>', dt.datetime(2020, 1, 1, 3, 0, tzinfo=pytz.UTC)),
                                conversion=activity_conversion)
            constrained_sources(s, ('start', '>', dt.datetime(2021, 1, 1, 3, 0, tzinfo=pytz.UTC)),
                                conversion=activity_conversion)
