
import datetime as dt

from urwid import Text, MainLoop, Frame, Padding, Filler, Pile, Columns, Divider, Edit

from .database import Database
from .log import make_log
from .utils import PALETTE
from .uweird.calendar import Calendar
from .uweird.database import SingleTableDynamic, DATE_ORDINAL
from .uweird.decorators import Border
from .uweird.focus import FocusAttr
from .uweird.tabs import TabManager


def make_widget(db, log, tab_manager):
    binder = SingleTableDynamic(db, log, 'diary',
                                transforms={'ordinal': DATE_ORDINAL},
                                defaults={'notes': ''}
                                )
    calendar = Calendar()
    binder.bind_key(calendar, 'ordinal')
    # notes = NoneProofEdit(caption="Notes: ")
    notes = Edit(caption="Notes: ")
    binder.bind(notes, 'notes')
    body = Filler(
        Pile([Divider(),
              Columns([(20, Padding(tab_manager.add(calendar), width='clip')),
                       ('weight', 1, tab_manager.add(FocusAttr(notes)))],
                      dividechars=2)]),
        valign='top')
    # trigger database read
    binder._save_widget_value(calendar, calendar.state)
    return Border(Frame(body, header=Text('Diary')))


def main(args):
    log = make_log(args)
    db = Database(args, log)
    tab_manager = TabManager()
    diary = make_widget(db, log, tab_manager)
    tab_manager.discover(diary)
    MainLoop(diary, palette=PALETTE).run()
