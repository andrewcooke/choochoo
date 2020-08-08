from logging import getLogger
from os import getpid
from time import time, sleep

import psutil as ps
from sqlalchemy import Column, Text, Integer, DateTime, distinct

from ..support import Base
from ..types import ShortCls, Name, short_cls
from ..utils import add
from ...common.date import to_time
from ...lib import now
from ...names import simple_name

log = getLogger(__name__)


class SystemConstant(Base):

    __tablename__ = 'system_constant'

    name = Column(Name, primary_key=True)
    value = Column(Text, nullable=False)

    @classmethod
    def from_name(cls, s, name, none=False):
        instance = s.query(SystemConstant).filter(SystemConstant.name == name).one_or_none()
        if instance is None:
            if not none:
                raise Exception(f'No value for {name}')
            else:
                log.debug(f'Read {name}=None')
                return None
        else:
            log.debug(f'Read {name}={instance.value}')
            return instance.value

    @classmethod
    def set(cls, s, name, value, force=False):
        if force:
            cls.delete(s, name)
        s.add(SystemConstant(name=name, value=value))
        s.commit()
        log.debug(f'Set {name}={value}')
        return value

    @classmethod
    def delete(cls, s, name):
        s.query(SystemConstant).filter(SystemConstant.name == name).delete()
        s.commit()

    TIMEZONE = 'timezone'
    JUPYTER_URL = 'jupyter-url'
    WEB_URL = 'web-url'
    LAST_GARMIN = 'last-garmin'
    DB_VERSION = 'db-version'
    LOG_COLOR = 'log-color'


class Process(Base):

    __tablename__ = 'process'

    id = Column(Integer, primary_key=True)
    owner = Column(ShortCls, nullable=False, index=True)
    pid = Column(Integer, nullable=False, unique=True)
    start = Column(DateTime(timezone=True), nullable=False, default=now)
    command = Column(Text, nullable=True)
    log = Column(Text, nullable=True)

    @classmethod
    def run(cls, s, owner, cmd, log_name):
        from ...pipeline.process import fmt_cmd
        popen = ps.Popen(args=cmd, shell=True)
        log.debug(f'Adding command [{fmt_cmd(cmd)}]; pid {popen.pid}')
        s.add(Process(command=cmd, owner=owner, pid=popen.pid, log=log_name))
        s.commit()
        return popen

    @classmethod
    def delete(cls, s, owner, pid, delta_seconds=3):
        process = s.query(Process).filter(Process.owner == owner, Process.pid == pid).one()
        process.__kill(delta_seconds=delta_seconds)
        log.debug(f'Deleting record for process {process.pid}')
        s.delete(process)
        s.commit()

    @classmethod
    def delete_all(cls, s, owner, delta_seconds=3):
        for process in s.query(Process).filter(Process.owner == owner).all():
            if process.pid == getpid():
                log.debug(f'Not killing self (PID {process.pid})')
            else:
                process.__kill(delta_seconds=delta_seconds)
                log.debug(f'Deleting record for process {process.pid}')
                s.delete(process)
        s.commit()

    @classmethod
    def exists_any(cls, s, owner=None, excluding=None):
        if owner:
            owners = [short_cls(owner)]
        else:
            owners = [row[0] for row in s.query(distinct(Process.owner)).all()]
        owners = set(owners)
        if excluding:
            owners = owners.difference(short_cls(exc) for exc in excluding)
        for owner in owners:
            for process in s.query(Process).filter(Process.owner == owner).all():
                if process.__still_running():
                    return True
            cls.delete_all(s, owner)
        return False

    def __still_running(self, delta_seconds=3):
        return exists(self.pid, self.start, delta_seconds=delta_seconds)

    def __kill(self, delta_seconds=3):
        if self.__still_running(delta_seconds=delta_seconds):
            log.debug(f'Killing process {self.pid}')
            ps.Process(self.pid).kill()


# if we're given a delta time, the start time of the process and database records have to match
# (or it's some other unrelated process because the process counter wrapped round)
# if they don't match we return false because the original process is not running.
def exists(pid, start_time, delta_seconds=3, zombie_seconds=10):
    if not ps.pid_exists(pid):
        return False
    process = ps.Process(pid)
    if process.status() == ps.STATUS_ZOMBIE:
        try:
            log.warning(f'Waiting for zombie {pid}')
            process.wait(zombie_seconds)
        except ps.TimeoutExpired:
            log.debug(f'Timeout waiting for zombie {pid}')
        return False
    elif delta_seconds:
        creation_ok = abs(process.create_time() - start_time.timestamp()) < delta_seconds
        if creation_ok:
            log.debug(f'Process {pid} still exists')
        else:
            log.debug(f'Creation time for process {pid} incorrect ({process.create_time()} / {start_time.timestamp()})')
        return creation_ok
    else:
        log.debug(f'Assuming process {pid} is same as expected')
        return True   # if delta_seconds = 0 don't check, just assume same


