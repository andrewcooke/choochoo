
import datetime as dt

from sqlalchemy import or_
from urwid import MainLoop, Columns, Pile, Frame, Filler, Text, Divider, WEIGHT

from .args import DATE
from ..lib.date import to_date, local_date_to_time
from ..lib.io import tui
from ..lib.utils import PALETTE_RAINBOW, em
from ..lib.widgets import DateSwitcher
from ..squeal.tables.pipeline import PipelineType
from ..squeal.tables.source import disable_interval_cleaning, Source
from ..squeal.tables.topic import Topic, TopicJournal
from ..stoats.display import build_pipeline
from ..uweird.fields import PAGE_WIDTH
from ..uweird.tui.decorators import Border, Indent
from ..uweird.tui.factory import Factory
from ..uweird.tui.tabs import TabList
from ..uweird.tui.widgets import DividedPile


@tui
def diary(args, log, db):
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
    disable_interval_cleaning()
    TopicJournal.check_tz(db)
    MainLoop(Diary(log, db, date), palette=PALETTE_RAINBOW).run()


# todo - change to date + tz


class Diary(DateSwitcher):
    '''
    Render the diary at a given date.
    '''

    def _build(self, s):
        self._log.debug('Building diary at %s' % self._date)
        body, f = [], Factory(TabList())
        root_topics = [topic for topic in
                       s.query(Topic).filter(Topic.parent == None,
                                             or_(Topic.start <= self._date, Topic.start == None),
                                             or_(Topic.finish >= self._date, Topic.finish == None)).
                           order_by(Topic.sort).all()
                       if topic.schedule.at_location(self._date)]
        for topic in root_topics:
            body.append(self.__topic(s, f, topic))
        for extra in self.__pipeline(s, f):
            body.append(extra)
        body = Border(Frame(Filler(DividedPile(body), valign='top'),
                            header=Pile([Text(self._date.strftime('%Y-%m-%d - %A')), Divider()]),
                            footer=Pile([Divider(), Text(self.__footer(), align='center')])))
        return body, f.tabs

    def __footer(self):
        footer = ['meta-', em('q'), 'uit/e', em('x'), 'it/', em('s'), 'ave']
        footer += [' [shift]meta-']
        for sep, c in enumerate('dwmya'):
            if sep: footer += ['/']
            footer += [em(c)]
        footer += ['ctivity/', em('t'), 'oday']
        return footer

    def __topic(self, s, f, topic):
        self._log.debug('%s' % topic)
        body, title = [], None
        if topic.name:
            title = Text(topic.name)
        if topic.description:
            body.append(Text(topic.description))
        body += list(self.__fields(s, f, topic))
        body += list(self.__children(s, f, topic))
        if not body:
            return title
        body = Indent(Pile(body))
        if title:
            body = Pile([title, body])
        return body

    def __fields(self, s, f, topic):
        columns, width = [], 0
        for field in topic.fields:
            self._log.debug('%s' % field)
            tjournal = self.__topic_journal(s, topic)
            tjournal.populate(self._log, s)
            display = field.display_cls(self._log, s, tjournal.statistics[field],
                                        *field.display_args, **field.display_kargs)
            self._log.debug('%s' % display)
            if width + display.width > PAGE_WIDTH:
                yield Columns(columns)
                columns, width = [], 0
            columns.append((WEIGHT, display.width, f(display.bound_widget())))
            width += display.width
        if width:
            yield Columns(columns)

    def __children(self, s, f, topic):
        for child in topic.children:
            if child.schedule.at_location(self._date):
                extra = self.__topic(s, f, child)
                if extra:
                    yield extra

    def __topic_journal(self, s, topic):
        tjournal = s.query(TopicJournal). \
            filter(TopicJournal.topic == topic,
                   TopicJournal.date == self._date).one_or_none()
        if not tjournal:
            tjournal = TopicJournal(topic=topic, date=self._date, time=local_date_to_time(self._date))
            s.add(tjournal)
        return tjournal

    def __pipeline(self, s, f):
        yield from build_pipeline(self._log, s, PipelineType.DIARY, f, self._date)

    def save(self):
        if self._session:
            self.__interval_cleaning()
        super().save()

    def __interval_cleaning(self):
        # on exit:
        # - remove any journal entries with no data (all null)
        # - remove any intervals affected by journals with non-null data
        s, dirty = self._session, False
        for tjournal in s.query(TopicJournal).filter(TopicJournal.date == self._date).all():
            clean = True
            tjournal.populate(self._log, s)
            for field in tjournal.topic.fields:
                if tjournal.statistics[field].value is not None:
                    clean = False
                    break
            if clean:
                s.delete(tjournal)
            else:
                dirty = True
        if dirty:
            Source.clean_times(s, [local_date_to_time(self._date)])
