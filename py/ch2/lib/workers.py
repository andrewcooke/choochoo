from contextlib import contextmanager
from logging import getLogger
from os import getpid
from sys import argv
from time import sleep, time

from math import floor

from ..sql import Process
from ..sql.types import short_cls

log = getLogger(__name__)
DELTA_TIME = 3
SLEEP_TIME = 1
REPORT_TIME = 60
LOG = 'log'
LIKE = 'like'


class Workers:

    def __init__(self, system, n_parallel, owner, cmd):
        self.__system = system
        self.n_parallel = n_parallel
        self.owner = owner
        self.cmd = cmd
        self.__workers_to_logs = {}  # map from Popen to log index
        self.ch2 = command_root()
        self.clear_all()

    def clear_all(self):
        for worker in self.__workers_to_logs:
            log.warning(f'Killing PID {worker.pid} ({worker.args})')
            self.__system.delete_process(self.owner, worker.pid)
        self.__system.delete_all_processes(self.owner)

    def run(self, args):
        self.wait(self.n_parallel - 1)
        log_index = self._free_log_index()
        log_name = f'{short_cls(self.owner)}.{log_index}.{LOG}'
        cmd = (self.cmd + ' ' + args).format(log=log_name, ch2=self.ch2)
        worker = self.__system.run_process(self.owner, cmd, log_name)
        self.__workers_to_logs[worker] = log_index

    def wait(self, n_workers=0):
        last_report = 0
        while len(self.__workers_to_logs) > n_workers:
            if time() - last_report > REPORT_TIME:
                log.debug(f'Currently have {len(self.__workers_to_logs)} workers; waiting to drop to {n_workers}')
                last_report = time()
            for worker in list(self.__workers_to_logs.keys()):
                worker.poll()
                process = self.__system.get_process(self.owner, worker.pid)
                if worker.returncode is not None:
                    if worker.returncode:
                        msg = f'Command "{process.command}" exited with return code {worker.returncode} ' + \
                              f'see {process.log} for more info'
                        log.warning(msg)
                        self.clear_all()
                        raise Exception(msg)
                    else:
                        log.debug(f'Command "{process.command}" finished successfully')
                        del self.__workers_to_logs[worker]
                        self.__system.delete_process(self.owner, worker.pid)
            sleep(SLEEP_TIME)
        if last_report:
            log.debug(f'Now have {len(self.__workers_to_logs)} workers')

    def _free_log_index(self):
        used = set(self.__workers_to_logs.values())
        for i in range(self.n_parallel):
            if i not in used:
                return i
        raise Exception('No log available (too many workers)')


def command_root():
    try:
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
    except:
        log.warning('Cannot read /proc so assuming that ch2 is started on the command line as "ch2"')
        return 'ch2'


class ProgressTree:

    def __init__(self, size, parent=None):
        self.__size = size
        self.__progress = 0
        self.__children = []
        self.__parent = parent
        if parent:
            parent.register(self)

    def register(self, child):
        self.__children.append(child)
        if len(self.__children) > self.__size:
            raise Exception(f'Progress children exceeded size {len(self.__children)}/{self.__size}')

    def local_progress(self):
        if self.__children:
            return sum(child.local_progress() for child in self.__children) / self.__size
        else:
            return self.__progress / self.__size if self.__size else 1

    def progress(self):
        if self.__parent:
            return self.__parent.progress()
        else:
            return self.local_progress()

    def _log_progress(self):
        local = floor(100 * self.local_progress())
        progress = floor(100 * self.progress())
        log.info(f'Progress: {progress:3d}% (locally {local}%)')

    def increment(self, n=1):
        if self.__children:
            raise Exception('Incrementing a parent node')
        self.__progress += n
        if self.__progress > self.__size:
            raise Exception(f'Progress counter exceeded size {self.__progress}/{self.__size}')
        self._log_progress()

    def complete(self):
        self.__progress = self.__size
        self._log_progress()

    @contextmanager
    def increment_or_complete(self, n=1):
        try:
            yield None
            self.increment(n=n)
        except Exception as e:
            log.debug(f'Completing on {type(e)}: {e}')
            self.complete()
            raise


class SystemProgressTree(ProgressTree):

    def __init__(self, system, name, size):
        super().__init__(size)
        self.system = system
        self.name = name
        system.create_progress(name)

    def progress(self):
        progress = super().progress()
        self.system.update_progress(self.name, percentage=floor(100 * progress))
        return progress

