
import datetime as dt
from logging import getLogger

from sqlalchemy import or_
from urwid import MainLoop, Pile, Text, connect_signal, Padding

from .args import DATE, SCHEDULE, FAST, mm
from ..diary.database import read_daily
from ..diary.urwid import build
from ..jupyter.server import set_controller_session
from ..jupyter.template.activity_details import activity_details
from ..jupyter.template.all_activities import all_activities
from ..jupyter.template.compare_activities import compare_activities
from ..jupyter.template.health import health
from ..jupyter.template.similar_activities import similar_activities
from ..lib.date import to_date
from ..lib.io import tui
from ..lib.schedule import Schedule
from ..lib.utils import PALETTE_RAINBOW, PALETTE
from ..lib.widgets import DateSwitcher
from ..sql import PipelineType, DiaryTopic, DiaryTopicJournal
from ..sql.database import StatisticJournal
from ..stats.display import display_pipeline
from ..stats.pipeline import run_pipeline
from ..urwid.fields.summary import summary_columns
from ..urwid.tui.decorators import Indent
from ..urwid.tui.factory import Factory
from ..urwid.tui.fixed import Fixed
from ..urwid.tui.tabs import TabList
from ..urwid.tui.widgets import SquareButton

log = getLogger(__name__)


@tui
def diary2(args, db):
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
        DiaryTopicJournal.check_tz(s)
    if schedule:
        schedule = Schedule(schedule)
        if schedule.start or schedule.finish:
            raise Exception('Schedule must be open (no start or finish)')
        MainLoop(ScheduleDiary(db, date, schedule), palette=PALETTE_RAINBOW).run()
    else:
        MainLoop(DailyDiary(db, date), palette=PALETTE).run()
        if not args[FAST]:
            print('\n  Please wait while statistics are updated...')
            run_pipeline(db, PipelineType.STATISTIC)
            print(f'  ...done (thanks! - use {mm(FAST)} to avoid this, if the risk is worth it)\n')


class Diary(DateSwitcher):

    def __init__(self, db, date):
        super().__init__(db, date)

    def save(self):
        s = self._session
        if s:
            self.__clean(s, s.dirty, delete=True)
            self.__clean(s, s.new, delete=False)
        super().save()

    @staticmethod
    def __clean(s, instances, delete=False):
        log.debug(f'{len(instances)}')
        for instance in instances:
            if isinstance(instance, StatisticJournal):
                if instance.value == None:
                    log.debug(f'Discarding {instance}')
                    if delete:
                        s.delete(instance)
                    else:
                        s.expunge(instance)


class DailyDiary(Diary):
    '''
    Render the diary at a given date.
    '''

    def _build(self, s):
        log.debug('Building diary at %s' % self._date)
        model = list(read_daily(s, self._date))
        f = Factory(TabList())
        widget = build(model, f)
        return widget, f.tabs

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

    def _diary_topics(self, s):
        finish = self._schedule.next_frame(self._date)
        return s.query(DiaryTopic).filter(DiaryTopic.parent == None,
                                          or_(DiaryTopic.start < finish, DiaryTopic.start == None),
                                          or_(DiaryTopic.finish >= self._date, DiaryTopic.finish == None)). \
            order_by(DiaryTopic.sort).all()

    def _filter_diary_child(self, child):
        finish = self._schedule.next_frame(self._date)
        return (child.start is None or child.start < finish) and (child.finish is None or child.finish > self._date)

    def _display_diary_topic_fields(self, s, f, topic):
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
