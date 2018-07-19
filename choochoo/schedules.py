
from urwid import Edit, Columns

from .log import make_log
from .squeal.binders import Binder
from .squeal.database import Database
from .squeal.schedule import Schedule, ScheduleType
from .uweird.calendar import TextDate
from .uweird.decorators import Indent
from .uweird.factory import Factory
from .uweird.focus import FocusWrap, MessageBar
from .uweird.tabs import TabList
from .uweird.widgets import DynamicContent, DividedPile, Menu, ColText, ColSpace
from .widgets import App


class ScheduleWidget(FocusWrap):

    def __init__(self, log, tabs, bar):
        factory = Factory(tabs, bar)
        self.title = factory(Edit('Title: '))
        super().__init__(self.title)


class SchedulesEditor(FocusWrap):

    def __init__(self, log, session, bar, schedules):
        self.__log = log
        self.__session = session
        self.__bar = bar
        tabs = TabList()
        body = []
        for schedule in sorted(schedules):
            body.append(self.__nested(schedule, tabs))
        super().__init__(DividedPile(body))

    def __nested(self, schedule, tabs):
        widget = ScheduleWidget(self.__log, tabs, self.__bar)
        Binder(self.__log, self.__session, widget, instance=schedule)
        children = []
        for child in sorted(schedule.children):
            children.append(self.__nested(child, tabs))
        if children:
            widget = DividedPile([widget, Indent(DividedPile(children))])
        return widget


class SchedulesFilter(DynamicContent):

    # two-stage approach here
    # outer filter commits / reads from the database and redisplays the tree
    # inner editor works only within the session

    def __init__(self, log, session, bar):
        self.__tabs = TabList()
        factory = Factory(self.__tabs, bar)
        types = dict((type.id, type.name) for type in session.query(ScheduleType).all())
        self.type = factory(Menu('', types))
        self.date = factory(TextDate(log))
        super().__init__(log, session, bar)

    def _make(self):
        root_schedules = list(self._session.query(Schedule).filter(Schedule.parent_id == None).all())
        # todo - ordinals from date filter
        # todo - tabs
        # todo - apply (filter) button
        editor = SchedulesEditor(self._log, self._session, self._bar, root_schedules)
        body = [Columns([ColText('Filter: '),
                         (18, self.date),
                         ColText(' '),
                         self.type,
                         ColText(' [ Apply ]')
                         ]),
                editor]
        return DividedPile(body), self.__tabs


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
