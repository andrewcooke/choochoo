from contextlib import contextmanager
from logging import getLogger

from .database import SystemConstant, Process, Database
from ..commands.args import DB_VERSION, UNDEF
from ..common.config import BaseConfig
from ..common.log import first_line

log = getLogger(__name__)


class Config(BaseConfig):

    def __init__(self, args):
        super().__init__(args, Database, DB_VERSION)

    def _with(self, **kargs):
        return Config(self.args._with(**kargs))

    def get_constant(self, name, none=False):
        with self.db.session_context() as s:
            value = SystemConstant.from_name(s, name, none=none)
            return value

    def set_constant(self, name, value, force=False):
        log.debug(f'Setting {name}={value}')
        with self.db.session_context() as s:
            return SystemConstant.set(s, name, value, force=force)

    def delete_constant(self, name, default=UNDEF):
        log.debug(f'Deleting {name}')
        with self.default(default):
            with self.db.session_context() as s:
                SystemConstant.delete(s, name)

    def get_process(self, owner, pid):
        with self.db.session_context() as s:
            process = s.query(Process).filter(Process.owner == owner, Process.pid == pid).one_or_none()
            if process is None:
                raise Exception(f'Could not find entry for process {pid} (owner {owner})')
            s.expunge(process)
            return process

    def run_process(self, owner, cmd, log_name, constraint=None):
        with self.db.session_context() as s:
            return Process.run(s, owner, cmd, log_name, constraint=constraint)  # todo change order

    def delete_process(self, owner, pid, delta_seconds=3):
        with self.db.session_context() as s:
            Process.delete(s, owner, pid, delta_seconds=delta_seconds)

    def delete_all_processes(self, owner, delta_seconds=3, default=UNDEF, constraint=None):
        with self.default(default):
            with self.db.session_context() as s:
                Process.delete_all(s, owner, delta_seconds=delta_seconds, constraint=constraint)

    def exists_any_process(self, owner=None, excluding=None):
        with self.db.session_context() as s:
            return Process.exists_any(s, owner=owner, excluding=excluding)

    @contextmanager
    def default(self, value=UNDEF):
        try:
            yield
        except Exception as e:
            if value is UNDEF:
                raise
            else:
                log.warning(f'Error (probably missing database): {first_line(e)}')
                return value
