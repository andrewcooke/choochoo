
from logging import getLogger
from os import getpid
from time import time, sleep

import psutil as ps
from sqlalchemy import Column, Text, Integer, Float, UniqueConstraint

from ..support import SystemBase
from ..types import Time, ShortCls
from ..utils import add
from ...lib import now

log = getLogger(__name__)


class SystemConstant(SystemBase):

    __tablename__ = 'system_constant'

    name = Column(Text, primary_key=True)
    value = Column(Text, nullable=False)

    @classmethod
    def get(cls, s, name, none=False):
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
    JUPYTER_URL = 'jupyter_url'
    WEB_URL = 'web_url'
    LAST_GARMIN = 'last_garmin'
    DB_VERSION = 'db_version'


class Process(SystemBase):

    __tablename__ = 'process'

    id = Column(Integer, primary_key=True)
    owner = Column(ShortCls, nullable=False, index=True)
    pid = Column(Integer, nullable=False, index=True)
    start = Column(Time, nullable=False, default=time)
    command = Column(Text, nullable=True)
    log = Column(Text, nullable=True)

    @classmethod
    def run(cls, s, owner, cmd, log_name):
        process = ps.Popen(args=cmd, shell=True)
        log.debug(f'Adding command [{cmd}] (PID {process.pid})')
        s.add(Process(command=cmd, owner=owner, pid=process.pid, log=log_name))
        s.commit()
        return process

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
    def exists_any(cls, s, owner):
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
def exists(pid, time, delta_seconds=3, zombie_seconds=10):
    if not ps.pid_exists(pid):
        log.debug(f'Process {pid} does not exist')
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
        creation_ok = abs(process.create_time() - time.timestamp()) < delta_seconds
        if creation_ok:
            log.debug(f'Process {pid} still exists')
        else:
            log.debug(f'Creation time for process {pid} incorrect')
        return creation_ok
    else:
        log.debug(f'Assuming process {pid} is same as expected')
        return True   # if delta_seconds = 0 don't check, just assume same


class Progress(SystemBase):

    __tablename__ = 'progress'

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False, unique=True)
    pid = Column(Integer, nullable=False, index=True)
    start = Column(Time, nullable=False)
    percent = Column(Integer, nullable=False, default=0)
    error = Column(Text, nullable=True)

    def __str__(self):
        return f'Progress {self.name} / {self.pid}'

    @classmethod
    def create(cls, s, name, delta_seconds=3):
        progress = s.query(Progress).filter(Progress.name == name).one_or_none()
        if progress:
            if progress.percent != 100 and exists(progress.pid, progress.start, delta_seconds=delta_seconds):
                raise Exception(f'Progress {name} already exists (PID {progress.pid})')
            else:
                log.debug(f'Removing old progress {name} / {progress.pid}')
                s.delete(progress)
                s.commit()
        us = ps.Process(getpid())
        add(s, Progress(name=name, pid=us.pid, start=us.create_time()))

    @classmethod
    def update(cls, s, name, **kargs):
        progress = s.query(Progress).filter(Progress.name == name, Progress.pid == getpid()).one_or_none()
        if not progress:
            raise Exception(f'No existing progress for {name} / {getpid()}')
        for name in kargs:
            value = kargs[name]
            log.debug(f'Setting progress {name}={value}')
            if hasattr(progress, name):
                setattr(progress, name, value)
            else:
                raise AttributeError(name)

    @classmethod
    def get_percent(cls, s, name, delta_seconds=3):
        progress = s.query(Progress).filter(Progress.name == name).one_or_none()
        if progress is None or not exists(progress.pid, progress.start, delta_seconds=delta_seconds):
            log.debug(f'No percent for {name}')
            return None
        else:
            log.debug(f'Progress for {name} is {progress.percent}%')
            return progress.percent

    @classmethod
    def wait_for_progress(cls, s, name, timeout=60, delta_seconds=3, pause=1):

        def pid(progress):
            if progress:
                pid = progress.pid
                s.expire(progress)
                return pid

        log.debug(f'Waiting for progress {name}')
        start = now()
        initial = s.query(Progress).filter(Progress.name == name).one_or_none()
        log.debug(f'Initial progress: {initial}')
        if initial and exists(initial.pid, initial.start):
            return

        # use PIDs so that we don't need to worry about expired objects
        initial = pid(initial)
        while True:
            sleep(pause)
            current = pid(s.query(Progress).filter(Progress.name == name).one_or_none())
            log.debug(f'Waiting for PID - comparing {initial} and {current}')
            if current != initial:
                return
            elif (now() - start).total_seconds() >= timeout:
                raise Exception(f'Did not find progress {name} before {timeout}s')
