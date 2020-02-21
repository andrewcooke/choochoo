
import datetime as dt
from logging import getLogger

from urwid import MainLoop, connect_signal

from .args import DATE, SCHEDULE, FAST, mm
from ..diary.database import read_date, COMPARE_LINKS, read_schedule
from ..diary.views.urwid import build, layout_date, layout_schedule
from ..jupyter.server import set_controller, JupyterController
from ..jupyter.template.activity_details import activity_details
from ..jupyter.template.all_activities import all_activities
from ..jupyter.template.compare_activities import compare_activities
from ..jupyter.template.health import health
from ..jupyter.template.similar_activities import similar_activities
from ..lib.date import to_date, time_to_local_date, time_to_local_time, local_time_to_time
from ..lib.io import tui
from ..lib.schedule import Schedule
from ..lib.utils import PALETTE
from ..lib.widgets import DateSwitcher
from ..sql import PipelineType, DiaryTopicJournal, ActivityJournal
from ..sql.database import StatisticJournal
from ..stats.display.nearby import NEARBY_LINKS
from ..stats.pipeline import run_pipeline
from ..urwid.tui.factory import Factory
from ..urwid.tui.tabs import TabList

log = getLogger(__name__)


@tui
def diary(args, system, db):
    '''
## diary

    > ch2 diary [DATE]

The date can be an absolute day or the number of days previous.  So `ch2 diary 1` selects yesterday.

Display the daily diary.  Enter information here.

To exit, alt-q (or, without saving, alt-x).

    > ch2 diary (--month | --year | --schedule SCHEDULE) [DATE}

Display a summary for the month / year / schedule.
    '''
    set_controller(JupyterController(args, system))
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
        DiaryTopicJournal.check_tz(system, s)
    if schedule:
        schedule = Schedule(schedule)
        if schedule.start or schedule.finish:
            raise Exception('Schedule must be open (no start or finish)')
        MainLoop(ScheduleDiary(db, date, schedule), palette=PALETTE).run()
    else:
        MainLoop(DailyDiary(db, date), palette=PALETTE).run()
        if not args[FAST]:
            print('\n  Please wait while statistics are updated...')
            run_pipeline(system, db, PipelineType.STATISTIC)
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
        for instance in instances:
            if isinstance(instance, StatisticJournal):
                if instance.value == None:
                    log.debug(f'Discarding {instance}')
                    if delete:
                        s.delete(instance)
                    else:
                        s.expunge(instance)

    def _wire(self, active, name, callback):
        if name in active:
            for menu in active[name]:
                connect_signal(menu, 'click', callback)
            del active[name]


class DailyDiary(Diary):
    '''
    Render the diary at a given date.
    '''

    def _build(self, s):
        log.debug('Building diary at %s' % self._date)
        model = list(read_date(s, self._date))
        f = Factory(TabList())
        active, widget = build(model, f, layout_date)
        self._wire(active, NEARBY_LINKS, lambda m: self._change_date(to_date(m.state[0].split(' ')[0])))
        self._wire(active, COMPARE_LINKS, lambda m: self.__show_gui(*m.state))
        self._wire(active, 'health', lambda l: self.__show_health())
        self._wire(active, 'all-similar', lambda l: self.__show_similar(l.state[0]))
        if active:
            raise Exception(f'Unhandled links: {", ".join(active.keys())}')
        return widget, f.tabs

    def __show_gui(self, aj1, aj2, group):
        aj1t, aj2t = local_time_to_time(aj1), local_time_to_time(aj2) if aj2 else None
        aj1 = ActivityJournal.at_local_time(self._session, aj1)
        if aj2:
            compare_activities(aj1t, aj2t, aj1.activity_group.name)
        else:
            activity_details(aj1t, aj1.activity_group.name)

    def __show_similar(self, local_time):
        aj1 = ActivityJournal.at_local_time(self._session, local_time)
        similar_activities(aj1.start, aj1.activity_group.name)

    def __show_health(self):
        health()


class ScheduleDiary(Diary):
    '''
    Display summary data for the given schedule.
    '''

    def __init__(self, db, date, schedule):
        self._schedule = schedule
        super().__init__(db, schedule.start_of_frame(date))

    def _build(self, s):
        log.debug(f'Building diary at {self._date} for {self._schedule}')
        model = list(read_schedule(s, self._schedule, self._date))
        f = Factory(TabList())
        active, widget = build(model, f, layout_schedule)
        self._wire(active, 'all-activities', lambda l: self.__show_all())
        if active:
            raise Exception(f'Unhandled links: {", ".join(active.keys())}')
        return widget, f.tabs

    def __show_all(self):
        finish = self._schedule.next_frame(self._date)
        all_activities(self._date.strftime('%Y-%m-%d'), finish.strftime('%Y-%m-%d'))
