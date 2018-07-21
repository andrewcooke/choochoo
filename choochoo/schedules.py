
from urwid import Edit, Columns, Pile, CheckBox, connect_signal, Divider

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


TYPE_WIDTH = 18
DATE_WIDTH = 18


class ScheduleWidget(FocusWrap):

    def __init__(self, log, session, tabs, bar, types, type_names, default_type, editor, schedule):
        factory = Factory(tabs, bar)
        self.__instance = schedule
        self.__types = types
        self.__default_type = default_type
        self.__editor = editor
        self.type_id = factory(Menu('Type: ', type_names), tab=False)
        self.title = factory(Edit('Title: '))
        self.repeat = factory(Edit('Repeat: '), tab=False)
        self.start = factory(Nullable('Open', lambda state: TextDate(log, date=state)), tab=False)
        self.finish = factory(Nullable('Open', lambda state: TextDate(log, date=state)), tab=False)
        self.description = factory(Edit('Description: ', multiline=True))
        self.sort = factory(Edit('Sort: '), tab=False)
        self.has_notes = factory(CheckBox("Notes? "), tab=False)
        add_child = SquareButton('Add Child')
        delete = SquareButton('Delete')
        reset = SquareButton('Reset')
        body = [Columns([(TYPE_WIDTH, self.type_id),
                         ColText('  '),
                         ('weight', 3, self.title)]),
                Columns([self.repeat,
                         ColText('  '),
                         (DATE_WIDTH, self.start),
                         ColText('  '),
                         (DATE_WIDTH, self.finish)]),
                self.description,
                Columns([self.sort,
                         ColText('  '),
                         self.has_notes,
                         ColSpace(),
                         (11, factory(add_child, tab=False)),
                         (8, factory(delete, tab=False)),
                         (7, factory(reset, tab=False))])]
        super().__init__(Pile(body))
        binder = Binder(log, session, self, instance=schedule)
        connect_signal(add_child, 'click', lambda widget: self.__add_child())
        connect_signal(delete, 'click', lambda widget: binder.delete())
        connect_signal(reset, 'click', lambda widget: binder.reset())  # todo - children?

    def __add_child(self):
        type_id = self.__default_type.state
        self.__instance.children.append(Schedule(type_id=type_id, type=self.__types[type_id],
                                 has_notes=0, sort='', title=''))
        self.__editor.rebuild()


class SchedulesEditor(DynamicContent):

    def __init__(self, log, session, bar, schedules, ordinals, types, type_names, default_type):
        self.__schedules = schedules
        self.__ordinals = ordinals
        self.__types = types
        self.__type_names = type_names
        self.__default_type = default_type
        super().__init__(log, session, bar)

    def _make(self):
        tabs = TabList()
        body = []
        for schedule in sorted(self.__schedules):
            body.append(self.__nested(schedule, tabs))
        add_top_level = SquareButton('Add Parent')
        factory = Factory(tabs, self._bar)
        body.append(Columns([(12, factory(add_top_level, tab=False)), ColText('  '), ColSpace()]))
        connect_signal(add_top_level, 'click', lambda widget: self.__add_top_level())
        return DividedPile(body), tabs

    def __nested(self, schedule, tabs):
        widget = ScheduleWidget(self._log, self._session, tabs, self._bar, self.__types, self.__type_names,
                                self.__default_type, self, schedule)
        children = []
        for child in sorted(schedule.children):
            if child.at_location(self.__ordinals):
                children.append(self.__nested(child, tabs))
        if children:
            widget = DividedPile([widget, Indent(DividedPile(children), width=2)])
        return widget

    def __add_top_level(self):
        type_id = self.__default_type.state
        self.__schedules.append(Schedule(type_id=type_id, type=self.__types[type_id],
                                         has_notes=0, sort='', title=''))
        self.rebuild()

    def __add_child(self, parent):
        type_id = self.__default_type.state
        parent.children.append(Schedule(type_id=type_id, type=self.__types[type_id],
                                     has_notes=0, sort='', title=''))
        self.rebuild()


class SchedulesFilter(DynamicContent):

    # two-stage approach here
    # outer filter commits / reads from the database and redisplays the tree
    # inner editor works only within the session

    def __init__(self, log, session, bar):
        self.__tabs = TabList()
        factory = Factory(self.__tabs, bar)
        self.__types = dict((type.id, type) for type in session.query(ScheduleType).all())
        self.__type_names = dict((id, type.name) for id, type in self.__types.items())
        self.filter_type = Nullable('Any type', lambda state: Menu('', self.__type_names, state=state))
        self.filter_date = Nullable('Open', lambda state: TextDate(log, date=state))
        apply = SquareButton('Apply')
        discard = SquareButton('Discard')
        self.default_type = Menu('', self.__type_names)
        delete = SquareButton('Delete')
        self.new_type = Edit('New: ')
        add = SquareButton('Add')
        self.filter = Pile([
            Columns([ColText('Filter   '),
                     (DATE_WIDTH, factory(self.filter_date)),
                     ColText(' '),
                     (TYPE_WIDTH, factory(self.filter_type)),
                     ColSpace(),
                     (7, factory(apply)),
                     (9, factory(discard, tab=False)),
                     ]),
            Columns([ColText('Types    Default: '),
                     (TYPE_WIDTH, factory(self.default_type)),
                     ColText(' '),
                     (8, factory(delete, tab=False)),  # todo - only enable if no instances?
                     ColSpace(),
                     (TYPE_WIDTH, factory(self.new_type, tab=False)),
                     (5, factory(add, tab=False))]),
            Divider(div_char='-', top=1),
        ])
        connect_signal(apply, 'click', lambda widget: self.__filter(True))
        connect_signal(discard, 'click', lambda widget: self.__filter(False))
        connect_signal(delete, 'click', lambda widget: self.__delete_type())
        connect_signal(add, 'click', lambda widget: self.__add_type())
        self.__filter_tabs = len(self.__tabs)
        super().__init__(log, session, bar)

    def _make(self):
        query = self._session.query(Schedule).filter(Schedule.parent_id == None)
        type_id = self.filter_type.state
        if type_id is not None:
            query = query.filter(Schedule.type_id == type_id)
        root_schedules = list(query.all())
        self._log.debug('Found %d root schedules' % len(root_schedules))
        date = self.filter_date.state
        if date is not None:
            date = DateOrdinals(date)
            root_schedules = [schedule for schedule in root_schedules if schedule.at_location(date)]
            self._log.debug('Root schedules at %s: %d' % (date, len(root_schedules)))
        editor = SchedulesEditor(self._log, self._session, self._bar, root_schedules, date,
                                 self.__types, self.__type_names, self.default_type)
        # on initial call, add tabs; later calls replace them (keeping filter tabs)
        if len(self.__tabs) > self.__filter_tabs:
            self.__tabs[self.__filter_tabs] = editor
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

    def __add_type(self):
        pass  # todo

    def __delete_type(self):
        pass  # todo


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
