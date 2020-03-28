
from sqlalchemy.orm import sessionmaker

from .database import DatabaseBase, SystemConstant, Process
from .support import SystemBase
from ..commands.args import SYSTEM


class System(DatabaseBase):

    def __init__(self, args):
        super().__init__(SYSTEM, SystemConstant, SystemBase, args)

    def _sessionmaker(self):
        return sessionmaker(bind=self.engine, expire_on_commit=False)

    def get_constant(self, name, none=False):
        with self.session_context() as s:
            return SystemConstant.get(s, name, none=none)

    def set_constant(self, name, value, force=False):
        with self.session_context() as s:
            return SystemConstant.set(s, name, value, force=force)

    def delete_constant(self, name):
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

    def delete_process(self, owner, pid, delta_time=3):
        with self.session_context() as s:
            Process.delete(s, owner, pid, delta_time=delta_time)

    def delete_all_processes(self, owner, delta_time=3):
        with self.session_context() as s:
            Process.delete_all(s, owner, delta_time=delta_time)

    def exists_any_process(self, owner):
        with self.session_context() as s:
            return Process.exists_any(s, owner)
