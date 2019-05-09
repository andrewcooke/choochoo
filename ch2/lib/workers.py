
from logging import getLogger
from os import getpid
from sys import argv
from time import sleep, mktime, time

from psutil import pid_exists, Process

from ..squeal import SystemProcess
from ..squeal.types import short_cls

log = getLogger(__name__)
DELTA_TIME = 3
SLEEP_TIME = 1
REPORT_TIME = 60
LOG = 'log'
LIKE = 'like'


class Workers:

    def __init__(self, s, n_parallel, owner, cmd):
        self._s = s
        self.n_parallel = n_parallel
        self.owner = owner
        self.cmd = cmd
        self.__workers = {}  # map from Popen to log index
        self.ch2 = command_root()
        self.clear_all()

    def clear_all(self):
        for worker in self.__workers.keys():
            log.warning(f'Killing PID {worker.pid} ({worker.args})')
            SystemProcess.delete(self._s, self.owner, worker.pid)
        SystemProcess.delete_all(self._s, self.owner)

    def _read_pid(self, pid):
        return self._s.query(SystemProcess). \
            filter(SystemProcess.owner == self.owner,
                   SystemProcess.pid == pid).one()

    def run(self, args):
        self.wait(self.n_parallel - 1)
        log_index = self._free_log_index()
        log_name = f'{short_cls(self.owner)}.{log_index}.{LOG}'
        cmd = (self.cmd + ' ' + args).format(log=log_name, ch2=self.ch2)
        worker = SystemProcess.run(self._s, cmd, log_name, self.owner)
        self.__workers[worker] = log_index

    def wait(self, n_workers=0):
        last_report = 0
        while len(self.__workers) > n_workers:
            if time() - last_report > REPORT_TIME:
                log.debug(f'Currently have {len(self.__workers)} workers; waiting to drop to {n_workers}')
                last_report = time()
            for worker in list(self.__workers.keys()):
                worker.poll()
                process = self._read_pid(worker.pid)
                if worker.returncode is not None:
                    if worker.returncode:
                        msg = f'Command "{process.command}" exited with return code {worker.returncode} ' + \
                              f'see {process.log} for more info'
                        log.warning(msg)
                        self.clear_all()
                        raise Exception(msg)
                    else:
                        log.debug(f'Command "{process.command}" finished successfully')
                        del self.__workers[worker]
                        SystemProcess.delete(self._s, self.owner, worker.pid)
            sleep(SLEEP_TIME)
        if last_report:
            log.debug(f'Now have {len(self.__workers)} workers')

    def _free_log_index(self):
        used = set(self.__workers.values())
        for i in range(self.n_parallel):
            if i not in used:
                return i
        raise Exception('No log available (too many workers)')


def command_root():
    with open(f'/proc/{getpid()}/cmdline', 'rb') as f:
        line = f.readline()

        def parse():
            word = bytearray()
            for char in line:
                if char:
                    word.append(char)
                else:
                    yield word.decode('utf8')
                    word = bytearray()

        words = list(parse())
        if len(argv) > 1:
            i = words.index(argv[1])
            words = words[:i]
        ch2 = ' '.join(words)
        log.debug(f'Using command "{ch2}"')
        return ch2
