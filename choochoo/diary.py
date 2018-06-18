
import datetime as dt

from urwid import Text, MainLoop, Frame, Padding, Filler, Pile, Columns, Divider, Edit, WidgetWrap, connect_signal

from .uweird.database import SingleTableDynamic, DATE_ORDINAL, SingleTableStatic
from .uweird.widgets import ColText, Rating, Number
from .database import Database
from .log import make_log
from .utils import PALETTE
from .uweird.calendar import Calendar
from .uweird.decorators import Border
from .uweird.focus import FocusAttr
from .uweird.tabs import TabManager


# we can't avoid mixing TUI and database here.  most of the display has to update when
# the date changes on the calendar

class Injury(WidgetWrap):

    def __init__(self, tab_manager, binder, id, title):
        self._tab_manager = tab_manager
        pain_avg = tab_manager.add(FocusAttr(binder.bind(Rating(caption='average: ', state=0), 'pain_avg')), group=self)
        pain_peak = tab_manager.add(FocusAttr(binder.bind(Rating(caption='peak: ', state=0), 'pain_peak')), group=self)
        notes = tab_manager.add(FocusAttr(binder.bind(Edit(caption='Notes: ', edit_text=''), 'notes')), group=self)
        super().__init__(
            Pile([Columns([('weight', 1, Text(title)),
                           ('weight', 1, Columns([ColText('Pain - '),
                                                  (11, pain_avg),
                                                  (8, pain_peak),
                                                  ('weight', 1, Padding(Text(''))),
                                                  ])),
                            ]),
                  notes,
                  ]))

    def untab(self):
        self._tab_manager.remove(self)


class BaseWrap(WidgetWrap):

    def __init__(self, db, log, tab_manager, date=None):
        self._db = db
        self._log = log
        self._tab_manager = tab_manager
        super().__init__(self._make(date))

    def _make(self, date):
        raise NotImplemented()


class Injuries(BaseWrap):

    def __init__(self, db, log, tab_manager, date=None):
        self._old_state = []
        super().__init__(db, log, tab_manager, date=date)

    def _make(self, date):
        ordinal = date.toordinal()
        injuries = [(row['id'], row['title']) for row in self._db.db.execute('''
            select id, title from injury 
            where (start is null or start <= ?) and (finish is null or finish >=?)
        ''', (ordinal, ordinal)).fetchmany()]
        body = []
        for (id, title) in injuries:
            binder = SingleTableStatic(self._db, self._log, 'injury_diary',
                                       key_names=('ordinal', 'injury'),
                                       defaults={'ordinal': date.toordinal(), 'injury': id,
                                                 'notes': '', 'pain_avg': 0, 'pain_peak': 0},
                                       autosave=True)
            injury = Injury(self._tab_manager, binder, id, title)
            self._old_state.append(injury)
            body.append(Columns([ColText('  '), injury]))
            binder.read_row(
                self._db.db.execute('''select * from injury_diary where injury = ? and ordinal = ?''',
                                    (id, ordinal)).fetchone())
        return Pile([Text('Injuries'), Pile(body)])

    def rebuild(self, unused_widget, date):
        for injury in self._old_state:
            injury.untab()
        self._w = self._make(date)


class Diary(BaseWrap):

    def _make(self, date):
        if not date: date = dt.date.today()
        binder = SingleTableDynamic(self._db, self._log, 'diary',
                                    transforms={'ordinal': DATE_ORDINAL},
                                    defaults={'notes': '', 'rest_hr': 40, 'sleep': 8,
                                              'mood': 5, 'weather': ''})
        raw_calendar = Calendar(date)
        calendar = self._tab_manager.add(FocusAttr(binder.bind_key(raw_calendar, 'ordinal')))
        notes = self._tab_manager.add(FocusAttr(binder.bind(Edit(caption='Notes: '), 'notes')))
        rest_hr = self._tab_manager.add(FocusAttr(binder.bind(Number(caption='Rest HR: ', max=100), 'rest_hr')))
        sleep = self._tab_manager.add(FocusAttr(binder.bind(Number(caption='Sleep hrs: ', max=24), 'sleep')))
        mood = self._tab_manager.add(FocusAttr(binder.bind(Rating(caption='Mood: '), 'mood')))
        weather = self._tab_manager.add(FocusAttr(binder.bind(Edit(caption='Weather: '), 'weather')))
        injuries = Injuries(self._db, self._log, self._tab_manager, date)
        connect_signal(raw_calendar, 'change', injuries.rebuild)
        body = [Columns([(20, Padding(calendar, width='clip')),
                         ('weight', 1, Pile([notes,
                                             Divider(),
                                             Columns([rest_hr, sleep, mood]),
                                             weather
                                             ]))],
                        dividechars=2),
                Divider(),
                injuries]
        binder.bootstrap(date)
        body = Filler(Pile([Divider(), Pile(body)]), valign='top')
        return Border(Frame(body, header=Text('Diary')))


def main(args):
    log = make_log(args)
    db = Database(args, log)
    tab_manager = TabManager(log)
    diary = Diary(db, log, tab_manager)
    tab_manager.discover(diary)
    MainLoop(diary, palette=PALETTE).run()
