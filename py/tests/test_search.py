
from logging import getLogger
from tempfile import TemporaryDirectory

from sqlalchemy import create_engine, Integer, Column, union, select
from sqlalchemy.orm import declarative_base, sessionmaker, aliased

from ch2 import upload, BASE
from ch2.commands.args import V, bootstrap_db, DEV, UPLOAD
from ch2.commands.search import do_search
from ch2.common.args import m, mm
from ch2.config.profiles.acooke import acooke
from tests import LogTestCase, random_test_user

log = getLogger(__name__)


class TestSearch(LogTestCase):

    def test_search(self):

        user = random_test_user()
        with TemporaryDirectory() as f:
            config = bootstrap_db(user, mm(BASE), f, m(V), '5', configurator=acooke)

            with self.assertRaisesRegex(Exception, 'could not be validated'):
                do_search(config.db, ['active-distance > 100'])

            config = bootstrap_db(user, mm(BASE), f, m(V), '5', mm(DEV), UPLOAD,
                                  'data/test/source/personal/25822184777.fit')
            upload(config)
            do_search(config.db, ['active-distance > 100'])


class SQLAlchemyTest(LogTestCase):

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
