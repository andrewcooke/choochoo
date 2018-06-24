
import datetime as dt

from urwid import Text, MainLoop, Frame, Padding, Filler, Pile, Columns, Divider, Edit, WidgetWrap, connect_signal

from .database import Database
from .log import make_log
from .utils import PALETTE
from .uweird.calendar import Calendar
from .uweird.database import SingleTableDynamic, DATE_ORDINAL, SingleTableStatic
from .uweird.decorators import Border
from .uweird.tabs import TabList, TabNode, Root
from .uweird.widgets import ColText, Rating, ColSpace, Integer, Float


class DynamicContent(TabNode):

    def __init__(self, db, log, saves, date=None):
        self._db = db
        self._log = log
        self._saves = saves
        super().__init__(log, *self._make(date))

    def _make(self, date):
        # should return (node, tab_list)
        raise NotImplemented()

    def rebuild(self, date):
        node, tabs = self._make(date)
        self._w = node
        self.replace_all(tabs)


TAB_GROUP = 'diary'


class Injury(WidgetWrap):

    def __init__(self, tabs, binder, title):
        pain_avg = tabs.append(binder.bind(Rating(caption='average: ', state=0), 'pain_avg', default=None))
        pain_peak = tabs.append(binder.bind(Rating(caption='peak: ', state=0), 'pain_peak', default=None))
        pain_freq = tabs.append(binder.bind(Rating(caption='freq: ', state=0), 'pain_freq', default=None))
        notes = tabs.append(binder.bind(Edit(caption='Notes: ', edit_text='', multiline=True), 'notes', default=''))
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


class Injuries(DynamicContent):

    def _make(self, date):
        tabs = TabList()
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
                                       defaults={'ordinal': ordinal, 'injury': id})
            self._saves.append(binder.save)
            injury = Injury(tabs, binder, title)
            body.append(injury)
            binder.read_row(
                self._db.execute('''select * from injury_diary where injury = ? and ordinal = ?''',
                                    (id, ordinal)).fetchone())
        return Pile([Text('Injuries'), Padding(Pile(body), left=2)]), tabs


class Aim(WidgetWrap):

    def __init__(self, tabs, binder, title):
        notes = tabs.append(binder.bind(Edit(caption='Notes: ', edit_text=''), 'notes', default=''))
        super().__init__(
            Pile([Text(title),
                  notes,
                  ]))


class Aims(DynamicContent):

    def _make(self, date):
        tabs = TabList()
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
                                       defaults={'ordinal': ordinal, 'aim': id})
            self._saves.append(binder.save)
            aim = Aim(tabs, binder, title)
            body.append(aim)
            binder.read_row(
                self._db.execute('''select * from aim_diary where aim = ? and ordinal = ?''',
                                    (id, ordinal)).fetchone())
        return Pile([Text('Aims'), Padding(Pile(body), left=2)]), tabs


class Diary(Root):

    def __init__(self, db, log, date=None):
        if not date: date = dt.date.today()
        tabs = TabList()
        saves = []
        binder = SingleTableDynamic(db, log, 'diary',
                                    transforms={'ordinal': DATE_ORDINAL})
        saves.append(binder.save)
        raw_calendar = Calendar(log, date)
        calendar = tabs.append(binder.bind_key(raw_calendar, 'ordinal'))
        notes = tabs.append(binder.bind(Edit(caption='Notes: ', multiline=True), 'notes', default=''))
        rest_hr = tabs.append(binder.bind(Integer(caption='Rest HR: ', maximum=100), 'rest_hr', default=None))
        sleep = tabs.append(binder.bind(Float(caption='Sleep hrs: ', maximum=24, dp=1, units="hr"), 'sleep', default=None))
        mood = tabs.append(binder.bind(Rating(caption='Mood: '), 'mood', default=None))
        weather = tabs.append(binder.bind(Edit(caption='Weather: '), 'weather', default=''))
        weight = tabs.append(binder.bind(Float(caption='Weight: ', maximum=100, dp=2, units='kg'), 'weight', default=None))
        meds = tabs.append(binder.bind(Edit(caption='Meds: '), 'meds', default=''))
        self.injuries = tabs.append(Injuries(db, log, saves, date))
        self.aims = tabs.append(Aims(db, log, saves, date))
        body = [Columns([(20, Padding(calendar, width='clip')),
                         ('weight', 1, Pile([notes,
                                             Divider(),
                                             Columns([rest_hr, sleep, mood]),
                                             Columns([('weight', 2, weather), ('weight', 1, weight)]),
                                             meds,
                                             ]))],
                        dividechars=2),
                Divider(),
                self.injuries,
                Divider(),
                self.aims]
        binder.bootstrap(date)
        body = Filler(Pile([Divider(), Pile(body)]), valign='top')
        connect_signal(raw_calendar, 'change', self.date_change)
        super().__init__(log, Border(Frame(body, header=Text('Diary'))), tabs, saves=saves)

    def date_change(self, unused_widget, date):
        self.injuries.rebuild(date)
        self.aims.rebuild(date)
        self.discover()


def main(args):
    log = make_log(args)
    db = Database(args, log)
    diary = Diary(db, log)
    diary.discover()
    MainLoop(diary, palette=PALETTE).run()
