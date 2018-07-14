
import datetime as dt

from sqlalchemy import and_, or_
from urwid import Text, Padding, Pile, Columns, Divider, Edit, connect_signal

from .log import make_log
from .repeating import DateOrdinals, Specification
from .squeal.binders import Binder
from .squeal.database import Database
from .squeal.diary import Diary
from .squeal.injury import Injury
from .squeal.schedule import ScheduleType, Schedule
from .uweird.calendar import Calendar
from .uweird.factory import Factory
from .uweird.focus import FocusWrap, MessageBar
from .uweird.tabs import TabList, TabNode
from .uweird.widgets import ColText, Rating, ColSpace, Integer, Float, DividedPile
from .widgets import App


class DynamicContent(TabNode):

    def __init__(self, log, session, bar, date=None):
        self._log = log
        self._session = session
        self._bar = bar
        super().__init__(log, *self._make(date))

    def _make(self, date):
        # should return (node, tab_list)
        raise NotImplemented()

    def rebuild(self, date):
        node, tabs = self._make(date)
        self._w = node
        self.replace_all(tabs)


class InjuryWidget(FocusWrap):

    def __init__(self, tabs, bar, injury):
        factory = Factory(tabs, bar)
        self.pain_avg = factory(Rating(caption='average: '))
        self.pain_peak = factory(Rating(caption='peak: '))
        self.pain_freq = factory(Rating(caption='freq: '))
        self.notes = factory(Edit(caption='Notes: ', edit_text='', multiline=True))
        super().__init__(
            Pile([Columns([('weight', 1, Text(injury.title)),
                           ('weight', 1, Columns([ColText('Pain - '),
                                                  (11, self.pain_avg),
                                                  (8, self.pain_peak),
                                                  (9, self.pain_freq),
                                                  ColSpace(),
                                                  ])),
                           ]),
                  self.notes,
                  ]))


class Injuries(DynamicContent):

    def _make(self, date):
        tabs = TabList()
        body = []
        for injury in self._session.query(Injury).filter(
                and_(or_(Injury.start == None, Injury.start <= date),
                     or_(Injury.finish == None, Injury.finish >= date))).\
                order_by(Injury.sort).all():
            widget = InjuryWidget(tabs, self._bar, injury)
            Binder(self._log, self._session, widget, Injury,
                   defaults={'id': injury.id, 'date': date})
            body.append(widget)
        if body:
            return DividedPile([Text('Injuries'), Padding(DividedPile(body), left=2)]), tabs
        else:
            return Pile([]), tabs


class ScheduleWidget(FocusWrap):

    def __init__(self, tabs, bar, schedule_type, schedule):
        factory = Factory(tabs, bar)
        body = [Text('%s: %s' % (schedule_type.name, schedule.title))]
        if schedule.has_notes:
            self.notes = factory(Edit(caption='Notes: ', edit_text='', multiline=True))
            body.append(self.notes)
        super().__init__(Pile(body))


class Schedules(DynamicContent):

    def _make(self, date):
        ordinals = DateOrdinals(date)
        tabs = TabList()
        body = []
        for schedule_type in self._session.query(ScheduleType).order_by(ScheduleType.sort).all():
            # todo nested schedules (parent_id)
            # todo indent
            for schedule in self._session.query(Schedule).filter(Schedule.type_id == schedule_type.id).\
                    filter(or_(Schedule.start == None, Schedule.start <= date),
                           or_(Schedule.finish == None, Schedule.finish >= date)).\
                    order_by(Schedule.sort).all():
                if schedule.repeat:
                    spec = Specification(schedule.repeat)
                    spec.start = schedule.start
                    spec.finish = schedule.finish
                    if not spec.frame().at_location(ordinals):
                        continue
                widget = ScheduleWidget(tabs, self._bar, schedule_type, schedule)
                Binder(self._log, self._session, widget, Schedule,
                       defaults={'id': schedule.id, 'date': date})
                body.append(widget)
        if body:
            return DividedPile([Text('Schedule'), Padding(DividedPile(body), left=2)]), tabs
        else:
            return Pile([]), tabs


class DiaryApp(App):

    def __init__(self, log, session, bar, date=None):
        self._session = session
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
        self.injuries = factory.tabs.append(Injuries(log, session, bar, date))
        # self.aims = factory.tabs.append(Aims(db, log, bar, saves, date))
        # self.reminders = Reminders(db, log, bar, saves, date)
        body = [Columns([(20, Padding(self.date, width='clip')),
                         ('weight', 1, Pile([self.notes,
                                             Divider(),
                                             Columns([self.rest_hr, self.sleep, self.mood]),
                                             Columns([('weight', 2, self.weather), ('weight', 1, self.weight)]),
                                             self.medication,
                                             ]))],
                        dividechars=2),
                # self.reminders,
                self.injuries,
                # self.aims,
                ]
        Binder(log, session, self, Diary, multirow=True, defaults={'date': dt.date.today()})
        connect_signal(calendar, 'change', self.date_change)
        super().__init__(log, 'Diary', bar, DividedPile(body), factory.tabs, session)

    def date_change(self, unused_widget, date):
        self._session.commit()
        self.injuries.rebuild(date)
        # self.aims.rebuild(date)
        # self.reminders.rebuild(date)
        self.root.discover()


def main(args):
    log = make_log(args)
    db = Database(args, log)
    bar = MessageBar()
    diary = DiaryApp(log, db.session(), bar)
    diary.run()
