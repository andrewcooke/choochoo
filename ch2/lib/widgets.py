
import datetime as dt
from abc import abstractmethod

from sqlalchemy import desc
from urwid import ExitMainLoop

from ..squeal.tables.activity import ActivityJournal
from .date import DAY, WEEK, MONTH, YEAR, add_duration, to_time, to_date
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

    def _session(self):
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
                self._change_date(c)
                return
            if c.lower() == 'a':
                self._change_activity(c)
                return
        return super().keypress(size, key)

    def _change_activity(self, c):
        s = self._session()
        q = s.query(ActivityJournal)
        if c == 'a':
            q = q.filter(ActivityJournal.time < to_time(self.__date)).order_by(desc(ActivityJournal.time))
        else:
            q = q.filter(ActivityJournal.time > to_time(self.__date)).order_by(ActivityJournal.time)
        journal = q.limit(1).one_or_none()
        if journal:
            self.__date = to_date(journal.time)
            self.rebuild()

    def _change_date(self, c):
        if c == '=':
            self.__date = dt.date.today()
        else:
            delta = (-1 if c == c.lower() else 1, c.lower())
            self.save()
            self.__date = to_date(add_duration(self.__date, delta))
        self.rebuild()

    def _build(self, session):
        return self._build_date(session, self.__date)

    @abstractmethod
    def _build_date(self, s, date):
        pass
