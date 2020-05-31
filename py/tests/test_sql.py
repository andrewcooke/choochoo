from logging import getLogger

import sqlalchemy as s
from sqlalchemy.orm import sessionmaker

from ch2.names import SPACE
from ch2.sql.support import Base
from ch2.sql.types import Date, simple_name
from tests import LogTestCase

log = getLogger(__name__)


class Data(Base):

    __tablename__ = 'data'

    integer = s.Column(s.Integer, primary_key=True)
    text = s.Column(s.Text, nullable=False, server_default='')
    date = s.Column(Date)


class Database:

    def __init__(self):
        self.engine = s.create_engine('sqlite:///:memory:', echo=True)
        self.__create_tables()
        self.session = sessionmaker(bind=self.engine)

    def __create_tables(self):
        log.info('Creating tables')
        Base.metadata.create_all(self.engine)


class TestName(LogTestCase):

    def test_tokenzie(self):
        self.assertEqual(simple_name('ABC 123 *^%'), 'abc-123-%')  # support for like
        self.assertEqual(simple_name('****'), SPACE)
        self.assertEqual(simple_name('123'), '-123')
        self.assertEqual(simple_name('Fitness 7d'), 'fitness-7d')
