

import datetime as dt

from sqlalchemy import or_
from urwid import MainLoop, ExitMainLoop, Columns, Pile, Frame, Filler, Text, Divider, WEIGHT

from ch2.uweird.tui.widgets import DividedPile
from .args import DATE
from ..lib.date import to_date
from ..lib.io import tui
from ..lib.utils import PALETTE
from ..squeal.database import Database
from ..squeal.tables.topic import Topic, TopicJournal
from ..uweird.fields import PAGE_WIDTH
from ..uweird.tui.decorators import Border, Indent
from ..uweird.tui.tabs import TabNode, TabList


@tui
def diary(args, log):
    '''
# diary

    ch2 diary [date]

The date can be an absolute day or the number of days previous.  So `ch2 diary 1` selects yesterday.

The daily diary.  Enter information here.

To exit, alt-q (or, without saving, alt-x).
    '''
    date = args[DATE]
    if not date:
        date = dt.date.today()
    else:
        try:
            date = to_date(date)
        except:
            date = dt.date.today() - dt.timedelta(days=int(date))
    db = Database(args, log)
    MainLoop(DiaryBuilder(log, db, date), palette=PALETTE).run()


class DiaryApp(TabNode):

    def __init__(self, log, db, date):
        self._log = log
        self.__db = db
        self.__session = None
        self.__date = date
        super().__init__(log, *self._build(self.__new_session(), self.__date))

    def __new_session(self):
        self.save()
        self.__session = self.__db.session()
        return self.__session

    def keypress(self, size, key):
        if key == 'meta q':
            self.save()
            raise ExitMainLoop()
        elif key == 'meta x':
            raise ExitMainLoop()
        elif key == 'meta s':
            self.save()
        else:
            return super().keypress(size, key)

    def save(self):
        if self.__session:
            self.__session.flush()
            self.__session.commit()


class DiaryBuilder(DiaryApp):

    def _build(self, s, date):
        self._log.debug('Building diary at %s' % date)
        body, tabs = [], TabList()
        root_topics = [topic for topic in
                       s.query(Topic).filter(Topic.parent == None,
                                             or_(Topic.start <= date, Topic.start == None),
                                             or_(Topic.finish >= date, Topic.finish == None)).
                                      order_by(Topic.sort).all()
                       if topic.schedule.at_location(date)]
        for started, topic in enumerate(root_topics):
            body.append(self._build_topic(s, topic, date))
        body = Border(Frame(Filler(DividedPile(body), valign='top'),
                            header=Pile([Text(date.strftime('%A %Y-%m-%d')), Divider()]),
                            footer=Pile([Divider(), Text('footer')])))
        return body, tabs

    def _build_topic(self, s, topic, date):
        self._log.debug(topic)
        body, title = [], None
        if topic.name:
            title = Text(topic.name)
        if topic.description:
            body.append(Text(topic.description))
        body += list(self._fields(s, topic, date))
        body += list(self._children(s, topic, date))
        if not body:
            return title
        body = Indent(Pile(body))
        if title:
            body = Pile([title, body])
        return body

    def _fields(self, s, topic, date):
        columns, width = [], 0
        for field in topic.fields:
            self._log.debug(field)
            journal = self._journal(s, topic, date)
            display = field.display_cls(self._log, s, journal.statistics[field], *field.display_args)
            self._log.debug(display)
            if width + display.width > PAGE_WIDTH:
                yield Columns(columns)
                columns, width = [], 0
            columns.append((WEIGHT, display.width, display.bound_widget()))
            width += display.width
        if width:
            yield Columns(columns)

    def _children(self, s, topic, date):
        for child in topic.children:
            if child.schedule.at_location(date):
                extra = self._build_topic(s, child, date)
                if extra:
                    yield extra

    def _journal(self, s, topic, date):
        journal = s.query(TopicJournal).filter(TopicJournal.topic == topic, TopicJournal.time == date).one_or_none()
        if not journal:
            journal = TopicJournal(topic=topic, time=date)
            s.add(journal)
        return journal
