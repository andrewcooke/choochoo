
from abc import ABC, abstractmethod
from logging import getLogger
from time import sleep

from .workers import command_root
from ..commands.args import VERBOSITY, BASE


log = getLogger(__name__)


class BaseController(ABC):

    def __init__(self, args, sys, server_cls, max_retries=5, retry_secs=3):
        self._base = args[BASE]
        self._sys = sys
        self.__server_cls = server_cls
        self.__max_retries = max_retries
        self.__retry_secs = retry_secs

    def status(self):
        if self._sys.exists_any_process(self.__server_cls):
            print('\n  Service running')
            self._status(True)
        else:
            print('\n  No service running')
            self._status(False)

    def _status(self, running):
        print()

    def start(self, restart=False):
        if self._sys.exists_any_process(self.__server_cls):
            log.debug('Service already running')
            if restart:
                self.stop()
            else:
                return
        log.debug('Starting remote service')
        ch2 = command_root()
        cmd, log_name = self._build_cmd_and_log(ch2)
        self._sys.run_process(self.__server_cls, cmd, log_name)
        retries = 0
        while not self._sys.exists_any_process(self.__server_cls):
            retries += 1
            if retries > self.__max_retries:
                raise Exception('Server did not start')
            sleep(self.__retry_secs)
        sleep(5)  # extra wait...
        log.info('Service started')

    @abstractmethod
    def _build_cmd_and_log(self, ch2):
        raise NotImplementedError()

    def stop(self):
        log.info('Stopping any running service')
        self._sys.delete_all_processes(self.__server_cls)
        self._cleanup()

    def _cleanup(self):
        pass

    def service(self):
        self.stop()
        log.info('Starting a local service')
        self._run()

    @abstractmethod
    def _run(self):
        raise NotImplementedError()
