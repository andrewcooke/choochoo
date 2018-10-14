
import datetime as dt
from logging import getLogger, basicConfig, DEBUG, StreamHandler, Formatter
from sys import stdout

import sqlalchemy as s
from sqlalchemy.orm import sessionmaker
from urwid import WidgetWrap, Pile, Edit, Filler

from ch2.squeal.binders import Binder
from ch2.squeal.support import Base
from ch2.squeal.types import Date
from ch2.uweird.tui.widgets import Integer

basicConfig()
log = getLogger()
log.setLevel(DEBUG)
handler = StreamHandler(stdout)
handler.setLevel(DEBUG)
formatter = Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
handler.setFormatter(formatter)
log.addHandler(handler)


class Data(Base):

    __tablename__ = 'data'

    integer = s.Column(s.Integer, primary_key=True)
    text = s.Column(s.Text, nullable=False, server_default='')
    date = s.Column(Date)


class Database:

    def __init__(self):
        self._log = log
        self.engine = s.create_engine('sqlite:///:memory:', echo=True)
        self.__create_tables()
        self.session = sessionmaker(bind=self.engine)

    def __create_tables(self):
        self._log.info('Creating tables')
        Base.metadata.create_all(self.engine)


class DataWidget(WidgetWrap):

    def __init__(self):
        self.integer = Integer('An integer: ')
        self.text = Edit('Some text: ')
        super().__init__(Filler(Pile([self.integer, self.text]), valign='top'))


def test_bind():

    db = Database()
    session = db.session()

    data = Data(integer=42, text='abc')
    session.add(data)
    widget = DataWidget()
    binder = Binder(log, session, widget, Data, defaults={'integer': 42})

    assert binder.instance.text == 'abc', binder.instance.text
    assert widget.text.edit_text == 'abc', widget.text.edit_text
    assert binder.instance.integer == 42, binder.instance.integer
    assert widget.integer.state == 42, widget.integer.state

    # edit the text
    size = (10,)
    for key in ('right', 'right', 'delete'):
        widget.text.keypress(size, key)
    assert widget.text.edit_text == 'ab', widget.text.edit_text
    assert binder.instance.text == 'ab', binder.instance.text
    assert binder.instance.integer == 42, binder.instance.integer

    # modify the primary key
    size = (10, 10)
    for key in ('right', 'right'):
        widget.integer.keypress(size, key)
    try:
        widget.integer.keypress(size, 'delete')
        assert False, 'expected error because primary key'
    except:
        pass

    session.expunge_all()
    # no need to add data - it was saved when the first binder above did a query
    widget = DataWidget()
    binder = Binder(log, session, widget, Data, multirow=True, defaults={'integer': 42})

    assert binder.instance.text == 'abc', binder.instance.text
    assert widget.text.edit_text == 'abc', widget.text.edit_text
    assert binder.instance.integer == 42, binder.instance.integer
    assert widget.integer.state == 42, widget.integer.state

    # edit the text
    size = (10,)
    for key in ('home', 'right', 'right', 'delete'):
        log.info('Keypress %s' % key)
        widget.text.keypress(size, key)
    assert widget.text.edit_text == 'ab', widget.text.edit_text
    assert binder.instance.text == 'ab', binder.instance.text
    assert binder.instance.integer == 42, binder.instance.integer

    # modify the primary key
    size = (10, 10)
    for key in ('right', 'right', 'delete'):
        widget.integer.keypress(size, key)

    assert binder.instance.integer == 4, binder.instance.integer
    assert binder.instance.text == '', binder.instance.text

    # and back again
    widget.integer.keypress(size, '2')
    assert binder.instance.integer == 42, binder.instance.integer
    assert binder.instance.text == 'ab', binder.instance.text

    # try setting date
    binder.instance.date = dt.date(2018, 7, 1)
    session.commit()
    data = session.query(Data).filter(Data.integer == 42).one()
    assert data.date == dt.date(2018, 7, 1)
