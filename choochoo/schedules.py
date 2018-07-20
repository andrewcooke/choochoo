
from urwid import Edit, Columns, Pile, CheckBox, connect_signal

from .lib.repeating import DateOrdinals
from .lib.widgets import App
from .log import make_log
from .squeal.binders import Binder
from .squeal.database import Database
from .squeal.schedule import Schedule, ScheduleType
from .uweird.calendar import TextDate
from .uweird.decorators import Indent
from .uweird.factory import Factory
from .uweird.focus import FocusWrap, MessageBar
from .uweird.tabs import TabList, TabNode
from .uweird.widgets import DynamicContent, DividedPile, Menu, ColText, ColSpace, Nullable, SquareButton


class ScheduleWidget(FocusWrap):

    def __init__(self, log, session, tabs, bar, types, schedule):
        factory = Factory(tabs, bar)
        self.type_id = factory(Menu('Type: ', types))
        self.title = factory(Edit('Title: '))
        self.repeat = factory(Edit('Repeat: '))
        self.start = factory(Nullable('Open', lambda state: TextDate(log, date=state)))
        self.finish = factory(Nullable('Open', lambda state: TextDate(log, date=state)))
        self.description = factory(Edit('Description: ', multiline=True))
        self.sort = factory(Edit('Sort: '))
        self.has_notes = factory(CheckBox("Notes? "))
        delete = SquareButton('Delete')
        reset = SquareButton('Reset')
        add_child = SquareButton('Add')
        body = [Columns([('weight', 1, self.type_id),
                         ColText('  '),
                         ('weight', 3, self.title)]),
                Columns([self.repeat,
                         ColText('  '),
                         self.start,
                         ColText('  '),
                         self.finish]),
                self.description,
                Columns([self.sort,
                         ColText('  '),
                         self.has_notes,
                         ColSpace(),
                         (7, add_child),
                         (10, delete),
                         (9, reset)])]
        super().__init__(Pile(body))
        binder = Binder(log, session, self, instance=schedule)
        connect_signal(delete, 'click', lambda widget: binder.delete())
        connect_signal(delete, 'click', lambda widget: binder.reset())


class SchedulesEditor(TabNode):

    def __init__(self, log, session, bar, schedules, ordinals, types):
        self.__log = log
        self.__session = session
        self.__bar = bar
        self.__ordinals = ordinals
        self.__types = types
        tabs = TabList()
        body = []
        for schedule in sorted(schedules):
            body.append(self.__nested(schedule, tabs))
        add_type = Menu('Type: ', types)
        add_top_level = SquareButton('Add')
        factory = Factory(tabs, bar)
        body.append(Columns([(7, factory(add_top_level)), ColText('  '), factory(add_type), ColSpace()]))
        super().__init__(log, DividedPile(body), tabs)

    def __nested(self, schedule, tabs):
        widget = ScheduleWidget(self.__log, self.__session, tabs, self.__bar, self.__types, schedule)
        children = []
        for child in sorted(schedule.children):
            if child.at_location(self.__ordinals):
                children.append(self.__nested(child, tabs))
        if children:
            widget = DividedPile([widget, Indent(DividedPile(children), width=2)])
        return widget


class SchedulesFilter(DynamicContent):

    # two-stage approach here
    # outer filter commits / reads from the database and redisplays the tree
    # inner editor works only within the session

    def __init__(self, log, session, bar):
        self.__tabs = TabList()
        factory = Factory(self.__tabs, bar)
        self.__types = dict((type.id, type.name) for type in session.query(ScheduleType).all())
        self.type = Nullable('Any type', lambda state: Menu('', self.__types, state=state))
        self.date = Nullable('Any date', lambda state: TextDate(log, date=state))
        apply = SquareButton('Apply')
        discard = SquareButton('Discard')
        self.filter = Columns([ColText('Filter: '),
                               (18, factory(self.date)),
                               ColText(' '),
                               factory(self.type),
                               ColSpace(),
                               (9, factory(apply)),
                               (11, factory(discard)),
                               ])
        connect_signal(apply, 'click', lambda widget: self.__filter(True))
        connect_signal(discard, 'click', lambda widget: self.__filter(False))
        super().__init__(log, session, bar)

    def _make(self):
        query = self._session.query(Schedule).filter(Schedule.parent_id == None)
        type_id = self.type.state
        if type_id is not None:
            query = query.filter(Schedule.type_id == type_id)
        root_schedules = list(query.all())
        self._log.debug('Found %d root schedules' % len(root_schedules))
        date = self.date.state
        if date is not None:
            date = DateOrdinals(date)
            root_schedules = [schedule for schedule in root_schedules if schedule.at_location(date)]
            self._log.debug('Root schedules at %s: %d' % (date, len(root_schedules)))
        editor = SchedulesEditor(self._log, self._session, self._bar, root_schedules, date, self.__types)
        # on initial call, add tabs; later calls replace them (keeping filter tabs)
        if len(self.__tabs) > 4:
            self.__tabs[4] = editor
        else:
            self.__tabs.append(editor)
        return DividedPile([self.filter, editor]), self.__tabs

    def __filter(self, save):
        if save:
            self._session.flush()
            self._session.commit()
        else:
            self._session.expunge_all()
        self.rebuild()


class ScheduleApp(App):

    def __init__(self, log, session, bar):
        self.__session = session
        tabs = TabList()
        self.injuries = tabs.append(SchedulesFilter(log, session, bar))
        super().__init__(log, 'Schedules', bar, self.injuries, tabs, session)


def main(args):
    log = make_log(args)
    session = Database(args, log).session()
    ScheduleApp(log, session, MessageBar()).run()
