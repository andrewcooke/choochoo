from logging import getLogger

from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql.functions import count

from .database import SystemConstant, Process, MappedDatabase, sqlite_uri, Database, Interval
from .support import SystemBase
from .tables.system import Progress, DirtyInterval
from ..commands.args import SYSTEM, DB_EXTN, DATA
from ..lib.utils import grouper

log = getLogger(__name__)


class System(MappedDatabase):

    def __init__(self, base):
        super().__init__(sqlite_uri(base, name=SYSTEM), SystemConstant, SystemBase)
        version = self.get_constant(SystemConstant.DB_VERSION, none=True)
        if version:
            log.info(f'Database version {version}')
        else:
            log.warning('Database unconfigured')

    def _sessionmaker(self):
        return sessionmaker(bind=self.engine, expire_on_commit=False)

    def get_constant(self, name, none=False):
        with self.session_context() as s:
            value = SystemConstant.from_name(s, name, none=none)
            return value

    def set_constant(self, name, value, force=False):
        log.debug(f'Setting {name}={value}')
        with self.session_context() as s:
            return SystemConstant.set(s, name, value, force=force)

    def delete_constant(self, name):
        log.debug(f'Deleting {name}')
        with self.session_context() as s:
            SystemConstant.delete(s, name)

    def get_process(self, owner, pid):
        with self.session_context() as s:
            return s.query(Process). \
                filter(Process.owner == owner,
                       Process.pid == pid).one()

    def run_process(self, owner, cmd, log_name):
        with self.session_context() as s:
            return Process.run(s, owner, cmd, log_name)  # todo change order

    def delete_process(self, owner, pid, delta_seconds=3):
        with self.session_context() as s:
            Process.delete(s, owner, pid, delta_seconds=delta_seconds)

    def delete_all_processes(self, owner, delta_seconds=3):
        with self.session_context() as s:
            Process.delete_all(s, owner, delta_seconds=delta_seconds)

    def exists_any_process(self, owner):
        with self.session_context() as s:
            return Process.exists_any(s, owner)

    def create_progress(self, name, delta_seconds=3):
        with self.session_context() as s:
            Progress.create(s, name, delta_seconds=delta_seconds)

    def update_progress(self, name, **kargs):
        with self.session_context() as s:
            Progress.update(s, name, **kargs)

    def remove_progress(self, name):
        with self.session_context() as s:
            Progress.remove(s, name)

    def get_percent(self, name):
        with self.session_context() as s:
            return Progress.get_percent(s, name)

    def wait_for_progress(self, name, timeout=60):
        with self.session_context() as s:
            return Progress.wait_for_progress(s, name, timeout=timeout)

    def get_database(self, uri=None):
        if not uri: uri = self.get_constant(SystemConstant.DB_URI, none=True)
        if uri:
            return Database(uri)
        else:
            log.warning('No database URI configured')
            return None

    def record_dirty_intervals(self, ids):
        if ids:
            with self.session_context() as s:
                # this doesn't have to be exact or thread safe
                known = set(s.query(DirtyInterval.interval_id).all())
                count = 0
                for id in ids:
                    if id not in known:
                        s.add(DirtyInterval(interval_id=id))
                        known.add(id)
                        count += 1
            if count: log.warning(f'Marked {count} intervals as dirty')

    def get_dirty_intervals(self):
        with self.session_context() as s:
            return s.query(DirtyInterval).all()

    def delete_dirty_intervals(self, intervals):
        dirty_ids = set(d.id for d in intervals)
        with self.session_context() as s:
            for ids in grouper(dirty_ids, 900):  # avoid limit in sqlite older versions
                s.query(DirtyInterval).filter(DirtyInterval.id.in_(ids)).delete(synchronize_session=False)


class Data:

    def __init__(self, base):
        self.__base = base
        self.__sys = None
        self.__db = None

    @property
    def base(self):
        return self.__base

    @property
    def sys(self):
        if not self.__sys:
            self.__sys = System(self.__base)
        return self.__sys

    @property
    def db(self):
        if not self.__db:
            self.__db = self.sys.get_database()
        return self.__db

    def reset(self):
        self.__sys = None
        self.__db = None
