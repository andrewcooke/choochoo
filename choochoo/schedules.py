from urwid import Edit, Columns

from .widgets import App
from .log import make_log
from .squeal.database import Database
from .squeal.schedule import Schedule
from .uweird.factory import Factory
from .uweird.focus import FocusWrap, MessageBar
from .uweird.tabs import TabList
from .uweird.widgets import DynamicContent


class ScheduleWidget(FocusWrap):

    def __init__(self, log, tabs, bar):
        factory = Factory(tabs, bar)
        self.title = factory(Edit('Title: '))
        super().__init__(self.title)


class SchedulesEditor(FocusWrap):

    def __init__(self, log, session, bar, schedules):

        super().__init__()


class SchedulesFilter(DynamicContent):

    # two-stage approach here
    # outer filter commits / reads from the database and redisplays the tree
    # inner editor works only within the session

    def __init__(self, log, session, bar):
        self.__tabs = TabList()
        factory = Factory(self.__tabs, bar)
        # self.type = factory(TypeFilter())
        # self.date = factory(DateFilter())
        self.__tabs.append(TabList())  # for editor
        super().__init__(log, session, bar)

    def __read(self):
        pass

    def _make(self):
        # todo - type filter
        root_schedules = list(self._session.query(Schedule).filter(Schedule.parent_id == None).all())
        # todo - ordinals from date filter
        editor = SchedulesEditor(self._log, self._session, self._bar, root_schedules)
        body = [Columns(self.type, self.date), editor, ]
        return editor, self.__tabs


class ScheduleApp(App):

    def __init__(self, log, session, bar):
        self.__session = session
        tabs = TabList()
        self.injuries = tabs.append(SchedulesFilter(log, session, bar))
        super().__init__(log, 'Diary', bar, self.injuries, tabs, session)


def main(args):
    log = make_log(args)
    session = Database(args, log).session()
    ScheduleApp(log, session, MessageBar()).run()
