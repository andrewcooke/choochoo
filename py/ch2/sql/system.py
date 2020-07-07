from logging import getLogger

from .database import SystemConstant, Process, Database
from .tables.system import Progress
from ..commands.args import DB_VERSION
from ..common.sql import DataSource

log = getLogger(__name__)


class Data(DataSource):

    def __init__(self, args):
        super().__init__(args, Database, DB_VERSION)

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
