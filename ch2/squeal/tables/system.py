
from logging import getLogger
from time import time, mktime

from psutil import Popen, pid_exists, Process
from sqlalchemy import Column, Text, Integer

from ..support import Base
from ..types import Time, ShortCls

log = getLogger(__name__)


class SystemConstant(Base):

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
    JUPYTER_URL = 'jupyter-url'
    JUPYTER_DIR = 'jupyter-dir'


class SystemProcess(Base):

    __tablename__ = 'system_process'

    id = Column(Integer, primary_key=True)
    command = Column(Text, nullable=True)
    log = Column(Text, nullable=True)
    start = Column(Time, nullable=False, default=time)
    owner = Column(ShortCls, nullable=False, index=True)
    pid = Column(Integer, nullable=False, index=True)

    @classmethod
    def run(cls, s, cmd, log_name, owner):
        process = Popen(args=cmd, shell=True)
        log.debug(f'Adding command [{cmd}] (PID {process.pid})')
        s.add(SystemProcess(command=cmd, owner=owner, pid=process.pid, log=log_name))
        s.commit()
        return process

    @classmethod
    def delete(cls, s, owner, pid, delta_time=3):
        process = s.query(SystemProcess).filter(SystemProcess.owner == owner, SystemProcess.pid == pid).one()
        process.__kill(delta_time=delta_time)
        log.debug(f'Deleting process {process.pid}')
        s.delete(process)
        s.commit()

    @classmethod
    def delete_all(cls, s, owner, delta_time=3):
        for process in s.query(SystemProcess).filter(SystemProcess.owner == owner).all():
            process.__kill(delta_time=delta_time)
            log.debug(f'Deleting process {process.pid}')
            s.delete(process)
        s.commit()

    @classmethod
    def exists_any(cls, s, owner):
        for process in s.query(SystemProcess).filter(SystemProcess.owner == owner).all():
            if process.__still_running():
                return True
        cls.delete_all(s, owner)
        return False

    def __still_running(self, delta_time=3):
        if not pid_exists(self.pid):
            log.debug(f'PID {self.pid} does not exist')
            return False
        if not delta_time:
            return True
        actual = Process(self.pid).create_time()
        saved = self.start.timestamp()
        creation_ok = abs(actual - saved) < delta_time
        if not creation_ok:
            log.debug(f'Creation time for PID {self.pid} incorrect ({actual} / {saved})')
        return creation_ok

    def __kill(self, delta_time=3):
        if self.__still_running(delta_time=delta_time):
            log.debug(f'Killing process {self.pid}')
            Process(self.pid).kill()
