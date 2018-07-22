
from urwid import Edit, Columns, Pile, CheckBox, connect_signal, Divider, Text

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

    def __init__(self, log, session, types, type_names, editor, schedule, has_type):
        self.__instance = schedule
        self.__types = types
        self.__editor = editor
        factory = Factory()
        if has_type:
            self.type_id = factory(Menu('Type: ', type_names))
        self.title = factory(Edit('Title: '))
        self.repeat = factory(Edit('Repeat: '))
        self.start = factory(Nullable('Open', lambda state: TextDate(log, date=state)))
        self.finish = factory(Nullable('Open', lambda state: TextDate(log, date=state)))
        self.description = factory(Edit('Description: ', multiline=True))
        self.sort = factory(Edit('Sort: '))
        self.has_notes = factory(CheckBox("Notes? "))
        add_child = SquareButton('Add Child')
        delete = SquareButton('Delete')
        reset = SquareButton('Reset')
        if has_type:
            body = [Columns([(TYPE_WIDTH, self.type_id),
                             ColText('  '),
                             ('weight', 3, self.title)])]
        else:
            body = [self.title]
        body.extend([Columns([self.repeat,
                              ColText('  '),
                              (DATE_WIDTH, self.start),
                              ColText('  '),
                              (DATE_WIDTH, self.finish)]),
                     self.description,
                     Columns([self.sort,
                              ColText('  '),
                              self.has_notes,
                              ColSpace(),
                              (11, factory(add_child)),
                              (8, factory(delete)),
                              (7, factory(reset))])])
        super().__init__(Pile(body))
        binder = Binder(log, session, self, instance=schedule)
        connect_signal(add_child, 'click', lambda widget: self.__add_child())
        connect_signal(delete, 'click', lambda widget: binder.delete())
        connect_signal(reset, 'click', lambda widget: binder.reset())  # todo - children?

    def __add_child(self):
        self.__instance.children.append(Schedule(type_id=None, has_notes=0, sort='', title=''))
        self.__editor.rebuild()


class SchedulesEditor(DynamicContent):

    def __init__(self, log, session, bar, schedules, ordinals, types, type_names):
        self.__schedules = schedules
        self.__ordinals = ordinals
        self.__types = types
        self.__type_names = type_names
        super().__init__(log, session, bar)

    def _make(self):
        tabs = TabList()
        factory = Factory(tabs, self._bar)
        body = []
        for schedule in sorted(self.__schedules):
            body.append(self.__nested(schedule, factory))
        parent_type = Menu('Type: ', self.__type_names)
        add_top_level = SquareButton('Add Parent')
        body.append(Columns([(12, factory(add_top_level)), ColText('  '), factory(parent_type), ColSpace()]))
        connect_signal(add_top_level, 'click', lambda widget: self.__add_top_level(parent_type.state))
        return DividedPile(body), tabs

    def __nested(self, schedule, factory, has_type=True):
        widget = factory(ScheduleWidget(self._log, self._session, self.__types, self.__type_names,
                                        self, schedule, has_type))
        children = []
        for child in sorted(schedule.children):
            if child.at_location(self.__ordinals):
                children.append(self.__nested(child, factory, has_type=False))
        if children:
            widget = DividedPile([widget, Indent(DividedPile(children), width=2)])
        return widget

    def __add_top_level(self, type_id):
        self.__schedules.append(Schedule(type_id=type_id, type=self.__types[type_id],
                                         has_notes=0, sort='', title=''))
        self.rebuild()

    def __add_child(self, parent):
        parent.children.append(Schedule(type_id=None, has_notes=0, sort='', title=''))
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
        self.type_to_delete = Menu('', self.__type_names)
        delete = SquareButton('Delete')
        self.type_to_add = Edit('New: ')
        add = SquareButton('Add')
        self.filter = Pile([
            Columns([ColText('Filter   '),
                     (DATE_WIDTH, factory(self.filter_date)),
                     ColText(' '),
                     (TYPE_WIDTH, factory(self.filter_type)),
                     ColSpace(),
                     (7, factory(apply)),
                     (9, factory(discard)),
                     ]),
            Columns([(TYPE_WIDTH, factory(self.type_to_delete)),
                     ColText(' '),
                     (8, factory(delete)),  # todo - only enable if no instances?
                     ColSpace(),
                     (TYPE_WIDTH, factory(self.type_to_add)),
                     (5, factory(add))]),
            Divider(),
            Indent(
                Text('Controls above, and alt-q, write changes to the database.  ' +
                     'Edits below are in-memory and can be reverted.')),
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
                                 self.__types, self.__type_names)
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
