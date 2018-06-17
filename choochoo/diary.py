
import datetime as dt

from urwid import Text, MainLoop, Frame, Padding, Filler, Pile, Columns, Divider, Edit, WidgetWrap

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
        self._id = id
        self.notes = Edit(caption='Notes: ', edit_text='')
        self.pain_avg = Rating(caption='average: ', state=0)
        self.pain_peak = Rating(caption='peak: ', state=0)
        super().__init__(
            Pile([Columns([('weight', 1, Text(title)),
                           ('weight', 1, Columns([ColText('Pain - '),
                                                  (11, tab_manager.add(FocusAttr(self.pain_avg))),
                                                  (8, tab_manager.add(FocusAttr(self.pain_peak))),
                                                  ('weight', 1, Padding(Text(''))),
                                                  ])),
                            ]),
                  tab_manager.add(FocusAttr(self.notes)),
                  ]))


class BaseWrap(WidgetWrap):

    def __init__(self, db, log, tab_manager, date=None):
        self._db = db
        self._log = log
        self._tab_manager = tab_manager
        super().__init__(self._make(date))

    def _make(self, date):
        raise NotImplemented()


class Injuries(BaseWrap):

    def _make(self, date):
        ordinal = date.toordinal()
        injuries = [(row['id'], row['title']) for row in self._db.db.execute('''
            select id, title from injury 
            where (start is null or start <= ?) and (finish is null or finish >=?)
        ''', (ordinal, ordinal)).fetchmany()]
        body = []
        for (id, title) in injuries:
            body.append(Columns([ColText('  '), Injury(self._tab_manager, id, title)]))
        return Pile([Text('Injuries'), Pile(body)])


class Diary(BaseWrap):

    def _make(self, date):
        if not date: date = dt.date.today()
        self.calendar = Calendar(date)
        self.notes = Edit(caption="Notes: ")
        self.injuries = Injuries(self._db, self._log, self._tab_manager, date)
        body = [Columns([(20, Padding(self._tab_manager.add(self.calendar), width='clip')),
                         ('weight', 1, self._tab_manager.add(FocusAttr(self.notes)))],
                        dividechars=2),
                Divider(),
                self.injuries]
        body = Filler(Pile([Divider(), Pile(body)]), valign='top')
        return Border(Frame(body, header=Text('Diary')))


def main(args):
    log = make_log(args)
    db = Database(args, log)
    tab_manager = TabManager()
    diary = Diary(db, log, tab_manager)
    tab_manager.discover(diary)
    MainLoop(diary, palette=PALETTE).run()
