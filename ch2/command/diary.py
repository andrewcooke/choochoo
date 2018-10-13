
import datetime as dt

from sqlalchemy import or_
from urwid import MainLoop, Columns, Pile, Frame, Filler, Text, Divider, WEIGHT

from .args import DATE
from ..lib.date import to_date
from ..lib.io import tui
from ..lib.utils import PALETTE
from ..lib.widgets import DateSwitcher
from ..squeal.database import Database
from ..squeal.tables.topic import Topic, TopicJournal
from ..uweird.fields import PAGE_WIDTH
from ..uweird.tui.decorators import Border, Indent
from ..uweird.tui.factory import Factory
from ..uweird.tui.tabs import TabList
from ..uweird.tui.widgets import DividedPile


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
    MainLoop(Diary(log, db, date), palette=PALETTE).run()


class Diary(DateSwitcher):
    '''
    Render the diary at a given date.
    '''

    def _build_date(self, s, date):
        self._log.debug('Building diary at %s' % date)
        body, f = [], Factory(TabList())
        root_topics = [topic for topic in
                       s.query(Topic).filter(Topic.parent == None,
                                             or_(Topic.start <= date, Topic.start == None),
                                             or_(Topic.finish >= date, Topic.finish == None)).
                                      order_by(Topic.sort).all()
                       if topic.schedule.at_location(date)]
        for started, topic in enumerate(root_topics):
            body.append(self.__topic(s, f, topic, date))
        body = Border(Frame(Filler(DividedPile(body), valign='top'),
                            header=Pile([Text(date.strftime('%Y-%m-%d - %A')), Divider()]),
                            footer=Pile([Divider(), Text('footer')])))
        return body, f.tabs

    def __topic(self, s, f, topic, date):
        self._log.debug('%s' % topic)
        body, title = [], None
        if topic.name:
            title = Text(topic.name)
        if topic.description:
            body.append(Text(topic.description))
        body += list(self.__fields(s, f, topic, date))
        body += list(self.__children(s, f, topic, date))
        if not body:
            return title
        body = Indent(Pile(body))
        if title:
            body = Pile([title, body])
        return body

    def __fields(self, s, f, topic, date):
        columns, width = [], 0
        for field in topic.fields:
            self._log.debug('%s' % field)
            journal = self.__journal(s, topic, date)
            display = field.display_cls(self._log, s, journal.statistics[field],
                                        *field.display_args, **field.display_kargs)
            self._log.debug('%s' % display)
            if width + display.width > PAGE_WIDTH:
                yield Columns(columns)
                columns, width = [], 0
            columns.append((WEIGHT, display.width, f(display.bound_widget())))
            width += display.width
        if width:
            yield Columns(columns)

    def __children(self, s, f, topic, date):
        for child in topic.children:
            if child.schedule.at_location(date):
                extra = self.__topic(s, f, child, date)
                if extra:
                    yield extra

    def __journal(self, s, topic, date):
        journal = s.query(TopicJournal).filter(TopicJournal.topic == topic, TopicJournal.time == date).one_or_none()
        if not journal:
            journal = TopicJournal(topic=topic, time=date)
            s.add(journal)
        return journal
