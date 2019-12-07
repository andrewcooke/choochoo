
import datetime as dt
from abc import abstractmethod
from logging import getLogger

from sqlalchemy import or_
from urwid import MainLoop, Columns, Pile, Frame, Filler, Text, Divider, WEIGHT, connect_signal, Padding

from .args import DATE, SCHEDULE, FAST, mm
from ..lib.date import to_date
from ..lib.io import tui
from ..lib.schedule import Schedule
from ..lib.utils import PALETTE_RAINBOW, em, label
from ..lib.widgets import DateSwitcher
from ..sql import PipelineType, Topic, TopicJournal
from ..sql.database import ActivityJournal, StatisticJournal
from ..sql.utils import add
from ..stats.display import display_pipeline
from ..stats.display.nearby import nearby_any_time, fmt_nearby
from ..stats.pipeline import run_pipeline
from ..jupyter.server import set_controller_session
from ..jupyter.template.activity_details import activity_details
from ..jupyter.template.all_activities import all_activities
from ..jupyter.template.compare_activities import compare_activities
from ..jupyter.template.health import health
from ..jupyter.template.similar_activities import similar_activities
from ..urwid.fields import PAGE_WIDTH
from ..urwid.fields.summary import summary_columns
from ..urwid.tui.decorators import Border, Indent
from ..urwid.tui.factory import Factory
from ..urwid.tui.fixed import Fixed
from ..urwid.tui.tabs import TabList
from ..urwid.tui.widgets import DividedPile, ArrowMenu, SquareButton

log = getLogger(__name__)


@tui
def diary(args, db):
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
        days = None
        try:
            # try int first because we need to separate the case of days from years
            days = int(date)
            if days > 1000:
                days = None
        except ValueError:
            pass
        if days is None:
            date = to_date(date)
        else:
            date = dt.date.today() - dt.timedelta(days=days)
    with db.session_context() as s:
        TopicJournal.check_tz(s)
    if schedule:
        schedule = Schedule(schedule)
        if schedule.start or schedule.finish:
            raise Exception('Schedule must be open (no start or finish)')
        MainLoop(ScheduleDiary(db, date, schedule), palette=PALETTE_RAINBOW).run()
    else:
        MainLoop(DailyDiary(db, date), palette=PALETTE_RAINBOW).run()
        if not args[FAST]:
            print('\n  Please wait while statistics are updated...')
            run_pipeline(db, PipelineType.STATISTIC)
            print(f'  ...done (thanks! - use {mm(FAST)} to avoid this, if the risk is worth it)\n')


class Diary(DateSwitcher):

    def __init__(self, db, date):
        super().__init__(db, date)

    def save(self):
        s = self._session
        log.info(f'{bool(s)}')
        if s:
            self.__clean(s, s.dirty, delete=True)
            self.__clean(s, s.new, delete=False)
        super().save()

    def __clean(self, s, instances, delete=False):
        log.debug(f'{len(instances)}')
        for instance in instances:
            if isinstance(instance, StatisticJournal):
                if instance.value == None:
                    log.debug(f'Discarding {instance}')
                    if delete:
                        s.delete(instance)
                    else:
                        s.expunge(instance)

    def _build(self, s):
        log.debug('Building diary at %s' % self._date)
        body, f = [], Factory(TabList())
        root_topics = list(self._topics(s))
        for topic in root_topics:
            body.append(self.__display_topic(s, f, topic))
        for extra in self._display_pipeline(s, f):
            body.append(extra)
        for extra in self._display_gui(s, f):
            body.append(extra)
        self._check_body(body)
        body = Border(Frame(Filler(DividedPile(body), valign='top'),
                            header=Pile([self._header(), Divider()]),
                            footer=Pile([Divider(), Text(self.__footer(), align='center')])))
        return body, f.tabs

    @abstractmethod
    def _topics(self, s):
        pass

    @abstractmethod
    def _display_pipeline(self, s, f):
        pass

    @abstractmethod
    def _display_gui(self, s, f):
        pass

    @abstractmethod
    def _header(self):
        pass

    def _check_body(self, body):
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
        log.debug('%s' % topic)
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
        tjournal.populate(s)
        for field in topic.fields:
            if field in tjournal.statistics:  # might be outside schedule
                log.debug('%s' % field.display_cls)
                display = field.display_cls(tjournal.statistics[field], *field.display_args, **field.display_kargs)
                log.debug('%s' % display)
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
        yield from display_pipeline(s, f, self._date, self)

    def _display_gui(self, s, f):
        menus = list(self.__gui_menus(s, f))
        if menus:
            yield Pile([Text('Jupyter'), Indent(Pile(menus))])

    def __gui_menus(self, s, f):
        for aj1 in ActivityJournal.at_date(s, self._date):
            options = [(None, 'None')] + [(aj2, fmt_nearby(aj2, nb)) for aj2, nb in nearby_any_time(s, aj1)]
            menu = ArrowMenu(label('%s v ' % aj1.name), dict(options))
            connect_signal(menu, 'click', self.__show_gui, user_args=[s, aj1])
            button = SquareButton('All Similar')
            connect_signal(button, 'click', self.__show_similar, user_args=[s, aj1])
            yield Columns([f(menu), f(Padding(Fixed(button, 13), width='clip'))])
        button = SquareButton('Health')
        connect_signal(button, 'click', self.__show_health, user_args=[s, self._date])
        yield f(Padding(Fixed(button, 8), width='clip'))

    def __show_gui(self, s, aj1, w):
        set_controller_session(s)
        if w.state:
            compare_activities(aj1.start, w.state.start, aj1.activity_group.name)
        else:
            activity_details(aj1.start, aj1.activity_group.name)

    def __show_similar(self, s, aj1, w):
        set_controller_session(s)
        similar_activities(aj1.start, aj1.activity_group.name)

    def __show_health(self, s, date, w):
        log.debug(f'w {w} s {s} date {date}')
        set_controller_session(s)
        health()


class ScheduleDiary(Diary):
    '''
    Display summary data for the given schedule.
    '''

    def __init__(self, db, date, schedule):
        self._schedule = schedule
        super().__init__(db, self._refine_new_date(date))

    def _header(self):
        return Text(self._date.strftime('%Y-%m-%d') + ' - Summary for %s' % self._schedule.describe())

    def _check_body(self, body):
        if len(body) < 4:
            body.append(Indent(Text('Updating the database automatically deletes summary statistics that cover '
                                    + 'the modified data.  You probably need to re-generate the statistics by '
                                    + 'running `ch2 statistics`.')))

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
        yield from summary_columns(s, f, self._date, self._schedule, names)

    def _display_pipeline(self, s, f):
        yield from display_pipeline(s, f, self._date, self, schedule=self._schedule)

    def _display_gui(self, s, f):
        set_controller_session(s)
        button = SquareButton('All Activities')
        connect_signal(button, 'click', self.__show_all)
        yield Pile([Text('Jupyter'), Indent(f(Padding(Fixed(button, 16), width='clip')))])

    def __show_all(self, w):
        finish = self._schedule.next_frame(self._date)
        all_activities(self._date.strftime('%Y-%m-%d'), finish.strftime('%Y-%m-%d'))
