
from logging import getLogger, basicConfig, DEBUG, StreamHandler, Formatter
from sys import stdout

from sqlalchemy import Column, Integer, ForeignKey, create_engine
from sqlalchemy.event import listen
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql.functions import count

from ch2.squeal.support import Base

basicConfig()
log = getLogger()
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


def setup():

    db = Database()
    s = db.session()
    o1 = Other()
    s.add(o1)
    o2 = Other()
    s.add(o2)
    s.add(Child(parent_ref=o1, child_ref=o2))
    s.commit()
    return db


def assert_eq(a, b):
    assert a == b, '%s != %s' % (a, b)


def test_delete_child_instance():

    db = setup()
    s = db.session()
    c = s.query(Child).one()
    s.delete(c)
    assert_eq(s.query(count(Parent.id)).scalar(), 0)


def test_delete_child_sql():

    db = setup()
    s = db.session()
    s.query(Child).delete()
    # !!! this is because the ondelete cascade goes "the other way"
    assert_eq(s.query(count(Parent.id)).scalar(), 1)


def test_delete_parent_instance():

    db = setup()
    s = db.session()
    p = s.query(Parent).one()
    s.delete(p)
    assert_eq(s.query(count(Child.id)).scalar(), 0)


def test_delete_parent_sql():

    db = setup()
    s = db.session()
    s.query(Parent).delete()
    assert_eq(s.query(count(Child.id)).scalar(), 0)


def test_delete_child_ref_instance():

    db = setup()
    s = db.session()
    o = s.query(Child).one().child_ref
    s.delete(o)
    s.commit()
    s = db.session()
    # !!! this is because SQL deletes the child via cascade, but not the parent (see test_delete_child_sql)
    # (we don't have a backref on Other, so SQLAlchemy isn't going to do anything - have no idea if it would)
    assert_eq(s.query(count(Parent.id)).scalar(), 1)
    assert_eq(s.query(count(Child.id)).scalar(), 0)


def test_delete_parent_ref_instance():

    db = setup()
    s = db.session()
    o = s.query(Child).one().parent_ref
    s.delete(o)
    s.commit()
    s = db.session()
    assert_eq(s.query(count(Parent.id)).scalar(), 0)
    assert_eq(s.query(count(Child.id)).scalar(), 0)
