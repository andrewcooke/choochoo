from logging import getLogger

from sqlalchemy import create_engine, Integer, Column, union, select
from sqlalchemy.orm import declarative_base, sessionmaker

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


