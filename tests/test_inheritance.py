
from logging import getLogger, basicConfig, DEBUG, StreamHandler, Formatter
from sys import stdout
from unittest import TestCase

from sqlalchemy import Column, Integer, ForeignKey, create_engine
from sqlalchemy.event import listen
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql.functions import count

from ch2.squeal.support import Base

basicConfig()
log = getLogger()
if not log.handlers:
    log.setLevel(DEBUG)
    handler = StreamHandler(stdout)
    handler.setLevel(DEBUG)
    formatter = Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    handler.setFormatter(formatter)
    log.addHandler(handler)


class Database:

    def __init__(self):
        self._log = log
        self.engine = create_engine('sqlite:///:memory:', echo=True)
        listen(self.engine, 'connect', self.fk_pragma_on_connect)
        self.session = sessionmaker(bind=self.engine)
        Base.metadata.create_all(self.engine)

    @staticmethod
    def fk_pragma_on_connect(dbapi_con, con_record):
        dbapi_con.execute('pragma foreign_keys=ON')


class Parent(Base):

    __tablename__ = 'parent'

    id = Column(Integer, primary_key=True)
    type = Column(Integer, nullable=False)
    parent_ref_id = Column(Integer, ForeignKey('other.id', ondelete='cascade'))
    parent_ref = relationship('Other')

    __mapper_args__ = {
        'polymorphic_identity': 0,
        'polymorphic_on': type
    }


class Child(Parent):

    __tablename__ = 'child'

    id = Column(Integer, ForeignKey('parent.id', ondelete='cascade'), primary_key=True)
    child_ref_id = Column(Integer, ForeignKey('other.id', ondelete='cascade'))
    child_ref = relationship('Other')

    __mapper_args__ = {
        'polymorphic_identity': 1,
        'passive_deletes': True
    }


class Other(Base):

    __tablename__ = 'other'

    id = Column(Integer, primary_key=True)


class TestInheritance(TestCase):

    def database(self):
        db = Database()
        s = db.session()
        o1 = Other()
        s.add(o1)
        o2 = Other()
        s.add(o2)
        s.add(Child(parent_ref=o1, child_ref=o2))
        s.commit()
        return db

    def test_delete_child_instance(self):
        s = self.database().session()
        c = s.query(Child).one()
        s.delete(c)
        self.assertEqual(s.query(count(Parent.id)).scalar(), 0)

    def test_delete_child_sql(self):
        s = self.database().session()
        s.query(Child).delete()
        # !!! this is because the ondelete cascade goes "the other way"
        self.assertEqual(s.query(count(Parent.id)).scalar(), 1)

    def test_delete_parent_instance(self):
        s = self.database().session()
        p = s.query(Parent).one()
        s.delete(p)
        self.assertEqual(s.query(count(Child.id)).scalar(), 0)

    def test_delete_parent_sql(self):
        s = self.database().session()
        s.query(Parent).delete()
        self.assertEqual(s.query(count(Child.id)).scalar(), 0)

    def test_delete_child_ref_instance(self):
        db = self.database()
        s = db.session()
        o = s.query(Child).one().child_ref
        s.delete(o)
        s.commit()
        s = db.session()
        # !!! this is because SQL deletes the child via cascade, but not the parent (see test_delete_child_sql)
        # (we don't have a backref on Other, so SQLAlchemy isn't going to do anything - have no idea if it would)
        self.assertEqual(s.query(count(Parent.id)).scalar(), 1)
        self.assertEqual(s.query(count(Child.id)).scalar(), 0)

    def test_delete_parent_ref_instance(self):
        db = self.database()
        s = db.session()
        o = s.query(Child).one().parent_ref
        s.delete(o)
        s.commit()
        s = db.session()
        self.assertEqual(s.query(count(Parent.id)).scalar(), 0)
        self.assertEqual(s.query(count(Child.id)).scalar(), 0)
