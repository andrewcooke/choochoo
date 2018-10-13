
import datetime as dt
from abc import abstractmethod

from urwid import ExitMainLoop

from .date import DAY, WEEK, MONTH, YEAR, add_duration
from ..uweird.tui.tabs import TabNode


class App(TabNode):
    '''
    An urwid mainlopp, database session and tabs.
    '''

    def __init__(self, log, db):
        self._log = log
        self.__db = db
        self.__session = None
        super().__init__(log, *self._build(self.__new_session()))

    def __new_session(self):
        self.save()
        self.__session = self.__db.session()
        return self.__session

    def keypress(self, size, key):
        if key == 'meta q':
            self.save()
            raise ExitMainLoop()
        elif key == 'meta x':
            raise ExitMainLoop()
        elif key == 'meta s':
            self.save()
        else:
            return super().keypress(size, key)

    def save(self):
        if self.__session:
            self._log.debug('Flushing and committing')
            self.__session.flush()
            self.__session.commit()
            self.__session = None

    @abstractmethod
    def _build(self, session):
        pass

    def rebuild(self):
        widget, tabs = self._build(self.__new_session())
        self._w = widget
        self.replace(tabs)


class DateSwitcher(App):
    '''
    Extend App with shortcuts for changing date and rebuilding.
    '''

    def __init__(self, log, db, date):
        self.__date = date
        super().__init__(log, db)

    def keypress(self, size, key):
        if key.startswith('meta'):
            c = key[-1]
            if c.lower() in (DAY, WEEK, MONTH, YEAR, '='):
                self.__change_date(c)
                return
        return super().keypress(size, key)

    def __change_date(self, c):
        if c == '=':
            self.__date = dt.date.today()
        else:
            delta = (-1 if c == c.lower() else 1, c.lower())
            self.save()
            self.__date = add_duration(self.__date, delta)
        self.rebuild()
        return

    def _build(self, session):
        return self._build_date(session, self.__date)

    @abstractmethod
    def _build_date(self, s, date):
        pass
