
import datetime as dt

from urwid import Text, Padding, Pile, Columns, Divider, Edit, connect_signal

from .database import Database
from .log import make_log
from .uweird.calendar import Calendar
from .uweird.database import SingleTableDynamic, DATE_ORDINAL, SingleTableStatic
from .uweird.factory import Factory
from .uweird.focus import FocusWrap, MessageBar
from .uweird.tabs import TabList, TabNode
from .uweird.widgets import ColText, Rating, ColSpace, Integer, Float
from .widgets import App


class DynamicContent(TabNode):

    def __init__(self, db, log, bar, saves, date=None):
        self._db = db
        self._log = log
        self._bar = bar
        self._saves = saves
        super().__init__(log, *self._make(date))

    def _make(self, date):
        # should return (node, tab_list)
        raise NotImplemented()

    def rebuild(self, date):
        node, tabs = self._make(date)
        self._w = node
        self.replace_all(tabs)


class Injury(FocusWrap):

    def __init__(self, tabs, bar, binder, title):
        factory = Factory(tabs, bar, binder)
        pain_avg = factory(Rating(caption='average: '), bindto='pain_avg', default=None)
        pain_peak = factory(Rating(caption='peak: '), bindto='pain_peak', default=None)
        pain_freq = factory(Rating(caption='freq: '), bindto='pain_freq', default=None)
        notes = factory(Edit(caption='Notes: ', edit_text='', multiline=True), bindto='notes', default='')
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
            injury = Injury(tabs, self._bar, binder, title)
            body.append(injury)
            binder.read_row(
                self._db.execute('''select * from injury_diary where injury = ? and ordinal = ?''',
                                    (id, ordinal)).fetchone())
        return Pile([Text('Injuries'), Padding(Pile(body), left=2)]), tabs


class Aim(FocusWrap):

    def __init__(self, tabs, bar, binder, title):
        factory = Factory(tabs, bar, binder)
        notes = factory(Edit(caption='Notes: ', edit_text=''), bindto='notes', default='')
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
            aim = Aim(tabs, self._bar, binder, title)
            body.append(aim)
            binder.read_row(
                self._db.execute('''select * from aim_diary where aim = ? and ordinal = ?''',
                                    (id, ordinal)).fetchone())
        return Pile([Text('Aims'), Padding(Pile(body), left=2)]), tabs


class Diary(App):

    def __init__(self, db, log, bar, date=None):
        if not date: date = dt.date.today()
        factory = Factory(TabList(), bar,
                          SingleTableDynamic(db, log, 'diary', transforms={'ordinal': DATE_ORDINAL}))
        saves = []
        saves.append(factory.binder.save)
        raw_calendar = Calendar(log, bar, date)
        calendar = factory(raw_calendar, bindto='ordinal', key=True)
        notes = factory(Edit(caption='Notes: ', multiline=True), bindto='notes', default='')
        rest_hr = factory(Integer(caption='Rest HR: ', maximum=100), bindto='rest_hr', default=None)
        sleep = factory(Float(caption='Sleep hrs: ', maximum=24, dp=1, units="hr"), bindto='sleep', default=None)
        mood = factory(Rating(caption='Mood: '), message='2: sad; 4: normal; 6 happy', bindto='mood', default=None)
        weather = factory(Edit(caption='Weather: '), bindto='weather', default='')
        weight = factory(Float(caption='Weight: ', maximum=100, dp=1, units='kg'), bindto='weight', default=None)
        meds = factory(Edit(caption='Meds: '), bindto='meds', default='')
        self.injuries = factory.tabs.append(Injuries(db, log, bar, saves, date))
        self.aims = factory.tabs.append(Aims(db, log, bar, saves, date))
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
        factory.binder.bootstrap(date)
        connect_signal(raw_calendar, 'change', self.date_change)
        super().__init__(log, 'Diary', bar, Pile(body), factory.tabs, saves)

    def date_change(self, unused_widget, date):
        self.injuries.rebuild(date)
        self.aims.rebuild(date)
        self.root.discover()


def main(args):
    log = make_log(args)
    db = Database(args, log)
    bar = MessageBar()
    diary = Diary(db, log, bar)
    diary.run()
