
import datetime as dt

from urwid import Text, MainLoop, Frame, Padding, Filler, Pile, Columns, Divider, Edit, WidgetWrap, connect_signal

from .database import Database
from .log import make_log
from .utils import PALETTE
from .uweird.calendar import Calendar
from .uweird.database import SingleTableDynamic, DATE_ORDINAL, SingleTableStatic
from .uweird.decorators import Border
from .uweird.tabs import TabManager
from .uweird.widgets import ColText, Rating, Number, ColSpace


class Injury(WidgetWrap):

    def __init__(self, tab_manager, binder, title):
        self._tab_manager = tab_manager
        pain_avg = tab_manager.add(binder.bind(Rating(caption='average: ', state=0), 'pain_avg', default=0), group=self)
        pain_peak = tab_manager.add(binder.bind(Rating(caption='peak: ', state=0), 'pain_peak', default=0), group=self)
        notes = tab_manager.add(binder.bind(Edit(caption='Notes: ', edit_text=''), 'notes', default=''), group=self)
        super().__init__(
            Pile([Columns([('weight', 1, Text(title)),
                           ('weight', 1, Columns([ColText('Pain - '),
                                                  (11, pain_avg),
                                                  (8, pain_peak),
                                                  ColSpace(),
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
                                       defaults={'ordinal': date.toordinal(), 'injury': id},
                                       autosave=True)
            injury = Injury(self._tab_manager, binder, title)
            self._old_state.append(injury)
            body.append(injury)
            binder.read_row(
                self._db.db.execute('''select * from injury_diary where injury = ? and ordinal = ?''',
                                    (id, ordinal)).fetchone())
        return Pile([Text('Injuries'), Padding(Pile(body), left=2)])

    def rebuild(self, unused_widget, date):
        for injury in self._old_state:
            injury.untab()
        self._w = self._make(date)


class Diary(BaseWrap):

    def _make(self, date):
        if not date: date = dt.date.today()
        binder = SingleTableDynamic(self._db, self._log, 'diary',
                                    transforms={'ordinal': DATE_ORDINAL})
        raw_calendar = Calendar(date)
        calendar = self._tab_manager.add(binder.bind_key(raw_calendar, 'ordinal'))
        notes = self._tab_manager.add(binder.bind(Edit(caption='Notes: '), 'notes', default=''))
        rest_hr = self._tab_manager.add(binder.bind(Number(caption='Rest HR: ', max=100), 'rest_hr', default=40))
        sleep = self._tab_manager.add(binder.bind(Number(caption='Sleep hrs: ', max=24), 'sleep', default=8))
        mood = self._tab_manager.add(binder.bind(Rating(caption='Mood: '), 'mood', default=5))
        weather = self._tab_manager.add(binder.bind(Edit(caption='Weather: '), 'weather', default=''))
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
