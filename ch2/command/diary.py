
import datetime as dt
from abc import abstractmethod

from sqlalchemy import or_
from urwid import MainLoop, Columns, Pile, Frame, Filler, Text, Divider, WEIGHT, connect_signal, Padding

from ch2.bucket.page.activity_similarity import ActivitySimilarityPage
from ch2.uweird.tui.fixed import Fixed
from .args import DATE, SCHEDULE
from ch2.bucket.page.activity_journal import ActivityJournalPage
from ..bucket.server import singleton_server
from ..lib.date import to_date
from ..lib.io import tui
from ..lib.schedule import Schedule
from ..lib.utils import PALETTE_RAINBOW, em, label
from ..lib.widgets import DateSwitcher
from ..squeal.database import add, ActivityJournal
from ..squeal.tables.topic import Topic, TopicJournal
from ..stoats.display import display_pipeline
from ..stoats.display.nearby import nearby_any_time, fmt_nearby
from ..uweird.fields import PAGE_WIDTH
from ..uweird.fields.summary import summary_columns
from ..uweird.tui.decorators import Border, Indent
from ..uweird.tui.factory import Factory
from ..uweird.tui.tabs import TabList
from ..uweird.tui.widgets import DividedPile, ArrowMenu, SquareButton


@tui
def diary(args, log, db):
    '''
## diary

    > ch2 diary [DATE]

The date can be an absolute day or the number of days previous.  So `ch2 diary 1` selects yesterday.

Display the daily diary.  Enter information here.

To exit, alt-q (or, without saving, alt-x).

    > ch2 diary (--month | --year | --schedule SCHEDULE) [DATE}

Display a summary for the month / year / schedule.
    '''
    date, schedule = args[DATE], args[SCHEDULE]
    if not date:
        date = dt.date.today()
    else:
        try:
            date = to_date(date)
        except:
            date = dt.date.today() - dt.timedelta(days=int(date))
    with db.session_context() as s:
        TopicJournal.check_tz(log, s)
    server = singleton_server(log, {'/activity_journal': ActivityJournalPage(log, db),
                                    '/activity_similarity': ActivitySimilarityPage(log, db)})
    try:
        if schedule:
            schedule = Schedule(schedule)
            if schedule.start or schedule.finish:
                raise Exception('Schedule must be open (no start or finish)')
            MainLoop(ScheduleDiary(log, db, date, schedule), palette=PALETTE_RAINBOW).run()
        else:
            MainLoop(DailyDiary(log, db, date, server), palette=PALETTE_RAINBOW).run()
    finally:
        server.stop()


class Diary(DateSwitcher):

    def __init__(self, log, db, date, server):
        super().__init__(log, db, date)
        self._server = server

    def _build(self, s):
        self._log.debug('Building diary at %s' % self._date)
        body, f = [], Factory(TabList())
        root_topics = list(self._topics(s))
        for topic in root_topics:
            body.append(self.__display_topic(s, f, topic))
        for extra in self._display_pipeline(s, f):
            body.append(extra)
        for extra in self._display_gui(s, f):
            body.append(extra)
        body = Border(Frame(Filler(DividedPile(body), valign='top'),
                            header=Pile([self._header(), Divider()]),
                            footer=Pile([Divider(), Text(self.__footer(), align='center')])))
        return body, f.tabs

    @abstractmethod
    def _header(self):
        pass

    def __footer(self):
        footer = ['meta-', em('q'), 'uit/e', em('x'), 'it/', em('s'), 'ave']
        footer += [' [shift]meta-']
        for sep, c in enumerate('dwmya'):
            if sep: footer += ['/']
            footer += [em(c)]
        footer += ['ctivity/', em('t'), 'oday']
        return footer

    def __display_topic(self, s, f, topic):
        self._log.debug('%s' % topic)
        body, title = [], None
        if topic.name:
            title = Text(topic.name)
        if topic.description:
            body.append(Text(topic.description))
        body += list(self._display_fields(s, f, topic))
        body += list(self.__display_children(s, f, topic))
        if not body:
            return title
        body = Indent(Pile(body))
        if title:
            body = Pile([title, body])
        return body

    def __display_children(self, s, f, topic):
        for child in topic.children:
            if self._filter_child(child):
                extra = self.__display_topic(s, f, child)
                if extra:
                    yield extra

    def _filter_child(self, child):
        return child.schedule.at_location(self._date)

    def _display_gui(self, s, f):
        yield from []


class DailyDiary(Diary):
    '''
    Render the diary at a given date.
    '''

    def _topics(self, s):
        for topic in s.query(Topic).filter(Topic.parent == None,
                                           or_(Topic.start <= self._date, Topic.start == None),
                                           or_(Topic.finish >= self._date, Topic.finish == None)). \
                order_by(Topic.sort).all():
            if topic.schedule.at_location(self._date):
                yield topic

    def _header(self):
        return Text(self._date.strftime('%Y-%m-%d - %A'))

    def _display_fields(self, s, f, topic):
        columns, width = [], 0
        tjournal = self.__topic_journal(s, topic)
        tjournal.populate(self._log, s)
        for field in topic.fields:
            if field in tjournal.statistics:  # might be outside schedule
                self._log.debug('%s' % field)
                display = field.display_cls(self._log, tjournal.statistics[field],
                                            *field.display_args, **field.display_kargs)
                self._log.debug('%s' % display)
                if width + display.width > PAGE_WIDTH:
                    yield Columns(columns)
                    columns, width = [], 0
                columns.append((WEIGHT, display.width, f(display.widget())))
                width += display.width
        if width:
            yield Columns(columns)

    def __topic_journal(self, s, topic):
        tjournal = s.query(TopicJournal). \
            filter(TopicJournal.topic == topic,
                   TopicJournal.date == self._date).one_or_none()
        if not tjournal:
            tjournal = add(s, TopicJournal(topic=topic, date=self._date))
        return tjournal

    def _display_pipeline(self, s, f):
        yield from display_pipeline(self._log, s, f, self._date, self)

    def _display_gui(self, s, f):
        menus = list(self.__gui_menus(s, f))
        if menus:
            yield Pile([Text('GUI'), Indent(Pile(menus))])

    def __gui_menus(self, s, f):
        for aj1 in ActivityJournal.at_date(s, self._date):
            options = [(None, 'None')] + [(aj2, fmt_nearby(aj2, nb)) for aj2, nb in nearby_any_time(s, aj1)]
            menu = ArrowMenu(label('%s v ' % aj1.name), dict(options))
            connect_signal(menu, 'click', self.__show_gui, aj1)
            button = SquareButton('All Similar')
            connect_signal(button, 'click', self.__show_similar, aj1)
            yield Columns([f(menu), f(Padding(Fixed(button, 13), width='clip'))])

    def __show_gui(self, w, aj1):
        path = '/activity_journal?id=%d' % aj1.id
        if w.state:
            path += '&compare=%d' % w.state.id
        self._server.show(path)

    def __show_similar(self, w, aj1):
        self._server.show('/activity_similarity?id=%d' % aj1.id)


class ScheduleDiary(Diary):
    '''
    Display summary data for the given schedule.
    '''

    def __init__(self, log, db, date, schedule):
        self._schedule = schedule
        super().__init__(log, db, self._refine_new_date(date))

    def _header(self):
        return Text(self._date.strftime('%Y-%m-%d') + ' - Summary for %s' % self._schedule.describe())

    def _refine_new_date(self, date):
        return self._schedule.start_of_frame(date)

    def _topics(self, s):
        finish = self._schedule.next_frame(self._date)
        return s.query(Topic).filter(Topic.parent == None,
                                     or_(Topic.start < finish, Topic.start == None),
                                     or_(Topic.finish >= self._date, Topic.finish == None)). \
            order_by(Topic.sort).all()

    def _filter_child(self, child):
        finish = self._schedule.next_frame(self._date)
        return (child.start is None or child.start < finish) and (child.finish is None or child.finish > self._date)

    def _display_fields(self, s, f, topic):
        names = [field.statistic_name for field in topic.fields]
        yield from summary_columns(self._log, s, f, self._date, self._schedule, names)

    def _display_pipeline(self, s, f):
        yield from display_pipeline(self._log, s, f, self._date, self, schedule=self._schedule)

