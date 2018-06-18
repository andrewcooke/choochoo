
import datetime as dt

from urwid import Text, MainLoop, Frame, Padding, Filler, Pile, Columns, Divider, Edit, WidgetWrap, connect_signal

from .uweird.database import SingleTableDynamic, DATE_ORDINAL
from .uweird.widgets import ColText, Rating
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

    def __init__(self, tab_manager, id, title):
        self._tab_manager = tab_manager
        self._id = id
        self.pain_avg = tab_manager.add(FocusAttr(Rating(caption='average: ', state=0)))
        self.pain_peak = tab_manager.add(FocusAttr(Rating(caption='peak: ', state=0)))
        self.notes = tab_manager.add(FocusAttr(Edit(caption='Notes: ', edit_text='')))
        super().__init__(
            Pile([Columns([('weight', 1, Text(title)),
                           ('weight', 1, Columns([ColText('Pain - '),
                                                  (11, self.pain_avg),
                                                  (8, self.pain_peak),
                                                  ('weight', 1, Padding(Text(''))),
                                                  ])),
                            ]),
                  self.notes,
                  ]))

    def untab(self):
        self._tab_manager.remove(self.notes)
        self._tab_manager.remove(self.pain_avg)
        self._tab_manager.remove(self.pain_peak)


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
            injury = Injury(self._tab_manager, id, title)
            self._old_state.append(injury)
            body.append(Columns([ColText('  '), injury]))
        return Pile([Text('Injuries'), Pile(body)])

    def rebuild(self, unused_widget, date):
        for injury in self._old_state:
            injury.untab()
        self._w = self._make(date)


class Diary(BaseWrap):

    def _make(self, date):
        if not date: date = dt.date.today()
        binder = SingleTableDynamic(self._db, self._log, 'diary', transforms={'ordinal': DATE_ORDINAL})
        self.calendar = Calendar(date)
        binder.bind_key(self.calendar, 'ordinal')
        self.notes = Edit(caption="Notes: ")
        binder.bind(self.notes, 'notes')
        self.injuries = Injuries(self._db, self._log, self._tab_manager, date)
        connect_signal(self.calendar, 'change', self.injuries.rebuild)
        body = [Columns([(20, Padding(self._tab_manager.add(self.calendar), width='clip')),
                         ('weight', 1, self._tab_manager.add(FocusAttr(self.notes)))],
                        dividechars=2),
                Divider(),
                self.injuries]
        binder.bootstrap(date)
        body = Filler(Pile([Divider(), Pile(body)]), valign='top')
        return Border(Frame(body, header=Text('Diary')))


def main(args):
    log = make_log(args)
    db = Database(args, log)
    tab_manager = TabManager()
    diary = Diary(db, log, tab_manager)
    tab_manager.discover(diary)
    MainLoop(diary, palette=PALETTE).run()
