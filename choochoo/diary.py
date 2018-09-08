
import datetime as dt

from sqlalchemy import and_, or_
from urwid import Text, Padding, Pile, Columns, Divider, Edit, connect_signal

from .args import DATE
from .lib.date import parse_date
from .lib.io import tui
from .lib.widgets import App
from .squeal.binders import Binder
from .squeal.database import Database
from .squeal.tables.activity import ActivityDiary
from .squeal.tables.diary import Diary
from .squeal.tables.injury import Injury, InjuryDiary
from .squeal.tables.schedule import Schedule, ScheduleDiary
from .uweird.calendar import Calendar
from .uweird.decorators import Indent
from .uweird.factory import Factory
from .uweird.focus import FocusWrap, MessageBar
from .uweird.tabs import TabList
from .uweird.widgets import ColText, Rating, ColSpace, Integer, Float, DividedPile, DynamicContent


class DynamicDate(DynamicContent):

    def __init__(self, log, session, bar, date):
        self._date = date
        super().__init__(log, session, bar)

    def rebuild(self, date):
        self._date = date
        super().rebuild()


class InjuryWidget(FocusWrap):

    def __init__(self, tabs, bar, injury):
        factory = Factory(tabs, bar)
        self.pain_average = factory(Rating(caption='average: '))
        self.pain_peak = factory(Rating(caption='peak: '))
        self.pain_frequency = factory(Rating(caption='freq: '))
        self.notes = factory(Edit(caption='Notes: ', edit_text='', multiline=True))
        super().__init__(
            Pile([Columns([('weight', 1, Text(injury.title)),
                           ('weight', 1, Columns([ColText('Pain - '),
                                                  (11, self.pain_average),
                                                  (8, self.pain_peak),
                                                  (9, self.pain_frequency),
                                                  ColSpace(),
                                                  ])),
                           ]),
                  self.notes,
                  ]))


class Injuries(DynamicDate):

    def _make(self):
        tabs = TabList()
        body = []
        for injury in self._session.query(Injury).filter(
                and_(or_(Injury.start == None, Injury.start <= self._date),
                     or_(Injury.finish == None, Injury.finish >= self._date))). \
                order_by(Injury.sort).all():
            widget = InjuryWidget(tabs, self._bar, injury)
            Binder(self._log, self._session, widget, InjuryDiary,
                   defaults={'injury_id': injury.id, 'date': self._date})
            body.append(widget)
        if body:
            return DividedPile([Text('Injuries'), Padding(DividedPile(body), left=2)]), tabs
        else:
            return Pile([]), tabs


class ScheduleWidget(FocusWrap):

    def __init__(self, log, tabs, bar, schedule, show_type):
        log.debug('Schedule: %s' % schedule)
        factory = Factory(tabs, bar)
        if show_type:
            body = [Text('%s: %s' % (schedule.type.name, schedule.title))]
        else:
            body = [Text(schedule.title)]
        if schedule.has_notes:
            self.notes = factory(Edit(caption='Notes: ', edit_text='', multiline=True))
            body.append(self.notes)
        super().__init__(Pile(body))


class Schedules(DynamicDate):

    def _make(self):
        root_schedules = Schedule.query_root(self._session, date=self._date)
        tabs = TabList()
        body = []
        prev = None
        for schedule in root_schedules:
            if prev and prev.type != schedule.type:
                body.append(Divider())
            body.append(self.__make_schedule(tabs, schedule))
            prev = schedule
        if body:
            return DividedPile([Text('Schedule'), Indent(Pile(body), width=2)]), tabs
        else:
            return Pile([]), tabs

    def __make_schedule(self, tabs, schedule, show_type=True):
        widget = ScheduleWidget(self._log, tabs, self._bar, schedule, show_type)
        Binder(self._log, self._session, widget, table=ScheduleDiary,
               defaults={'date': self._date, 'schedule_id': schedule.id})
        children = []
        for child in sorted(schedule.children):
            if child.at_location(self._date):
                children.append(self.__make_schedule(tabs, child, show_type=False))
            else:
                self._log.debug('Child %s not at %s' % (child, self._date))
        if children:
            widget = DividedPile([widget, Indent(DividedPile(children), width=2)])
        return widget


class ActivityWidget(FocusWrap):

    def __init__(self, tabs, bar, activity):
        factory = Factory(tabs, bar)
        self.title = Text(activity.title)
        # self.start = Time()
        # self.finish = Time()
        self.notes = factory(Edit(caption='Notes: ', edit_text='', multiline=True))
        # todo - append stats
        body = [self.notes] + [Text('%s: %s' % (statistic.activity_statistics.name, statistic.fmt_value)) for statistic in activity.statistics]
        super().__init__(Pile([self.title, Indent(Pile(body))]))


class Activities(DynamicDate):

    def _make(self):
        tabs = TabList()
        body = []
        for activity in self._session.query(ActivityDiary).filter(ActivityDiary.date == self._date).\
                order_by(ActivityDiary.start).all():
            widget = ActivityWidget(tabs, self._bar, activity)
            Binder(self._log, self._session, widget, ActivityDiary, defaults={'id': activity.id})
            body.append(widget)
        return Pile(body), tabs


class DiaryApp(App):

    def __init__(self, log, session, bar, date=None):

        self._log = log
        self.__session = session
        if not date: date = dt.date.today()
        factory = Factory(TabList(), bar)

        calendar = Calendar(log, bar, date)  # raw value needed below for signal
        self.date = factory(calendar)
        self.notes = factory(Edit(caption='Notes: ', multiline=True))
        self.rest_hr = factory(Integer(caption='Rest HR: ', maximum=100))
        self.sleep = factory(Float(caption='Sleep hrs: ', maximum=24, dp=1, units="hr"))
        self.mood = factory(Rating(caption='Mood: '), message='2: sad; 4: normal; 6 happy')
        self.weather = factory(Edit(caption='Weather: '))
        self.weight = factory(Float(caption='Weight: ', maximum=100, dp=1, units='kg'))
        self.medication = factory(Edit(caption='Meds: '))
        # order important here - binder re-binds on change and so muct come last(!)
        connect_signal(calendar, 'change', self.date_change)
        Binder(log, session, self, Diary, multirow=True, defaults={'date': date})

        self.injuries = factory.tabs.append(Injuries(log, session, bar, date=date))
        self.schedules = factory.tabs.append(Schedules(log, session, bar, date=date))
        self.activities = factory.tabs.append(Activities(log, session, bar, date=date))

        body = [Columns([(20, Padding(self.date, width='clip')),
                         ('weight', 1, Pile([self.notes,
                                             Divider(),
                                             Columns([self.rest_hr, self.sleep, self.mood]),
                                             Columns([('weight', 2, self.weather), ('weight', 1, self.weight)]),
                                             self.medication,
                                             self.activities,
                                             ]))],
                        dividechars=2),
                self.injuries,
                self.schedules,
                ]
        super().__init__(log, 'Diary', bar, DividedPile(body), factory.tabs, session)

    def date_change(self, _widget, date):
        self._log.debug('Date change: %s' % date)
        self.__session.commit()
        self.injuries.rebuild(date)
        self.schedules.rebuild(date)
        self.activities.rebuild(date)
        self.root.discover()


@tui
def diary(args, log):
    '''
# diary

    ch2 diary

The daily diary.  Select the date using the calendar and then enter daily information.

To exit, alt-q (or, without saving, alt-x).
    '''
    session = Database(args, log).session()
    if args[DATE]:
        date = parse_date(args[DATE])
    else:
        date = None
    DiaryApp(log, session, MessageBar(), date=date).run()
