from logging import getLogger
from os import environ

from .database import SystemConstant, Process, Database
from .tables.system import Progress
from ..commands.args import BASE, USER, PASS, VERSION, DB_VERSION
from ..common.names import URI

log = getLogger(__name__)


class Data:

    def __init__(self, args):
        self.__fmt_keys = {BASE: self.__read(args, BASE),
                           USER: self.__read(args, USER),
                           PASS: self.__read(args, PASS),
                           VERSION: DB_VERSION}
        self.__base = self.__fmt_keys[BASE]  # todo - still needed?
        self.__uri = self.__read(args, URI)
        self.__db = None

    def __read(self, args, name):
        '''Environment overrides command line so that system config overrides user preferences.'''
        env_name = 'CH2_' + name.upper()
        if env_name in environ:
            value = environ[env_name]
            log.debug(f'{name}={value} (from {env_name})')
        else:
            value = args[name]
            if name == PASS:
                log.debug(f'{name}=xxxxxx (from args)')
            else:
                log.debug(f'{name}={value} (from args)')
        return value

    @property
    def base(self):
        return self.__base

    @property
    def db(self):
        if not self.__db:
            self.__db = self.get_database()
        return self.__db

    def reset(self):
        self.__sys = None
        self.__db = None

    def get_constant(self, name, none=False):
        with self.db.session_context() as s:
            value = SystemConstant.from_name(s, name, none=none)
            return value

    def set_constant(self, name, value, force=False):
        log.debug(f'Setting {name}={value}')
        with self.db.session_context() as s:
            return SystemConstant.set(s, name, value, force=force)

    def delete_constant(self, name):
        log.debug(f'Deleting {name}')
        with self.db.session_context() as s:
            SystemConstant.delete(s, name)

    def get_safe_uri(self, uri=None, **kwargs):
        keys = dict(kwargs)
        keys[PASS] = 'xxxxxx'
        return self.get_uri(uri=uri, **keys)

    def get_uri(self, uri=None, **kwargs):
        if not uri: uri = self.__uri
        keys = dict(self.__fmt_keys)
        keys.update(**kwargs)
        return uri.format(**keys)

    def get_database(self, uri=None):
        safe_uri = self.get_safe_uri(uri=uri)
        log.debug(f'Connecting to {safe_uri}')
        uri = self.get_uri(uri=uri)
        return Database(uri)

    def get_process(self, owner, pid):
        with self.db.session_context() as s:
            process = s.query(Process).filter(Process.owner == owner, Process.pid == pid).one()
            s.expunge(process)
            return process

    def run_process(self, owner, cmd, log_name):
        with self.db.session_context() as s:
            return Process.run(s, owner, cmd, log_name)  # todo change order

    def delete_process(self, owner, pid, delta_seconds=3):
        with self.db.session_context() as s:
            Process.delete(s, owner, pid, delta_seconds=delta_seconds)

    def delete_all_processes(self, owner, delta_seconds=3):
        with self.db.session_context() as s:
            Process.delete_all(s, owner, delta_seconds=delta_seconds)

    def exists_any_process(self, owner):
        with self.db.session_context() as s:
            return Process.exists_any(s, owner)

    def create_progress(self, name, delta_seconds=3):
        with self.db.session_context() as s:
            Progress.create(s, name, delta_seconds=delta_seconds)

    def update_progress(self, name, **kargs):
        with self.db.session_context() as s:
            Progress.update(s, name, **kargs)

    def remove_progress(self, name):
        with self.db.session_context() as s:
            Progress.remove(s, name)

    def get_percent(self, name):
        with self.db.session_context() as s:
            return Progress.get_percent(s, name)

    def wait_for_progress(self, name, timeout=60):
        with self.db.session_context() as s:
            return Progress.wait_for_progress(s, name, timeout=timeout)

