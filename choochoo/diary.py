
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


class Maker(WidgetWrap):

    def __init__(self, db, log, tab_manager, date=None):
        self._db = db
        self._log = log
        self._tab_manager = tab_manager
        super().__init__(self._make(date))

    def _make(self, date):
        raise NotImplemented()

    def rebuild(self, date):
        self._w = self._make(date)


TAB_GROUP = 'diary'


class Injury(WidgetWrap):

    def __init__(self, tab_manager, binder, title):
        self._tab_manager = tab_manager
        pain_avg = tab_manager.add(binder.bind(Rating(caption='average: ', state=0), 'pain_avg', default=None), group=TAB_GROUP)
        pain_peak = tab_manager.add(binder.bind(Rating(caption='peak: ', state=0), 'pain_peak', default=None), group=TAB_GROUP)
        pain_freq = tab_manager.add(binder.bind(Rating(caption='freq: ', state=0), 'pain_freq', default=None), group=TAB_GROUP)
        notes = tab_manager.add(binder.bind(Edit(caption='Notes: ', edit_text='', multiline=True),
                                            'notes', default=''), group=TAB_GROUP)
        super().__init__(
            Pile([Columns([('weight', 1, Text(title)),
                           ('weight', 1, Columns([ColText('Pain - '),
                                                  (11, pain_avg),
                                                  (8, pain_peak),
                                                  (9, pain_freq),
                                                  ColSpace(),
                                                  ])),
                           ]),
                  notes,
                  ]))


class Injuries(Maker):

    def _make(self, date):
        ordinal = date.toordinal()
        injuries = [(row['id'], row['title']) for row in self._db.execute('''
            select id, title from injury 
            where (start is null or start <= ?) and (finish is null or finish >=?)
            order by sort
        ''', (ordinal, ordinal))]
        body = []
        for (id, title) in injuries:
            binder = SingleTableStatic(self._db, self._log, 'injury_diary',
                                       key_names=('ordinal', 'injury'),
                                       defaults={'ordinal': ordinal, 'injury': id},
                                       autosave=True)
            injury = Injury(self._tab_manager, binder, title)
            body.append(injury)
            binder.read_row(
                self._db.execute('''select * from injury_diary where injury = ? and ordinal = ?''',
                                    (id, ordinal)).fetchone())
        return Pile([Text('Injuries'), Padding(Pile(body), left=2)])


class Aim(WidgetWrap):

    def __init__(self, tab_manager, binder, title):
        self._tab_manager = tab_manager
        notes = tab_manager.add(binder.bind(Edit(caption='Notes: ', edit_text=''), 'notes', default=''), group=TAB_GROUP)
        super().__init__(
            Pile([Text(title),
                  notes,
                  ]))


class Aims(Maker):

    def _make(self, date):
        ordinal = date.toordinal()
        aims = [(row['id'], row['title']) for row in self._db.execute('''
            select id, title from aim 
            where (start is null or start <= ?) and (finish is null or finish >=?)
            order by sort
        ''', (ordinal, ordinal))]
        self._log.debug('Aims: %s (%d)' % (aims, len(aims)))
        body = []
        for (id, title) in aims:
            binder = SingleTableStatic(self._db, self._log, 'aim_diary',
                                       key_names=('ordinal', 'aim'),
                                       defaults={'ordinal': ordinal, 'aim': id},
                                       autosave=True)
            aim = Aim(self._tab_manager, binder, title)
            body.append(aim)
            binder.read_row(
                self._db.execute('''select * from aim_diary where aim = ? and ordinal = ?''',
                                    (id, ordinal)).fetchone())
        return Pile([Text('Aims'), Padding(Pile(body), left=2)])


class Diary(Maker):

    def _make(self, date):
        if not date: date = dt.date.today()
        binder = SingleTableDynamic(self._db, self._log, 'diary',
                                    transforms={'ordinal': DATE_ORDINAL})
        raw_calendar = Calendar(date)
        calendar = self._tab_manager.add(binder.bind_key(raw_calendar, 'ordinal'))
        notes = self._tab_manager.add(binder.bind(Edit(caption='Notes: ', multiline=True), 'notes', default=''))
        rest_hr = self._tab_manager.add(binder.bind(Number(caption='Rest HR: ', max=100), 'rest_hr', default=None))
        sleep = self._tab_manager.add(binder.bind(Number(caption='Sleep hrs: ', max=24), 'sleep', default=None))
        mood = self._tab_manager.add(binder.bind(Rating(caption='Mood: '), 'mood', default=None))
        weather = self._tab_manager.add(binder.bind(Edit(caption='Weather: '), 'weather', default=''))
        meds = self._tab_manager.add(binder.bind(Edit(caption='Meds: '), 'meds', default=''))
        self.injuries = Injuries(self._db, self._log, self._tab_manager, date)
        self.aims = Aims(self._db, self._log, self._tab_manager, date)
        body = [Columns([(20, Padding(calendar, width='clip')),
                         ('weight', 1, Pile([notes,
                                             Divider(),
                                             Columns([rest_hr, sleep, mood]),
                                             weather,
                                             meds,
                                             ]))],
                        dividechars=2),
                Divider(),
                self.injuries,
                Divider(),
                self.aims]
        binder.bootstrap(date)
        body = Filler(Pile([Divider(), Pile(body)]), valign='top')
        connect_signal(raw_calendar, 'change', self.rebuild)
        return Border(Frame(body, header=Text('Diary')))

    def rebuild(self, unused_widget, date):
        self._tab_manager.remove(TAB_GROUP)
        self.injuries.rebuild(date)
        self.aims.rebuild(date)


def main(args):
    log = make_log(args)
    db = Database(args, log)
    tab_manager = TabManager(log)
    diary = Diary(db, log, tab_manager)
    tab_manager.discover(diary)
    MainLoop(diary, palette=PALETTE).run()
