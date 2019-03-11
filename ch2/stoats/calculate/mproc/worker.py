
from os import getpid
from subprocess import Popen
from sys import argv
from time import sleep

from psutil import pid_exists, Process

from ....squeal import SystemProcess
from ....squeal.types import short_cls

DELTA_TIME = 3
SLEEP = 0.1
LOG = 'log'
LIKE = 'like'


class Workers:

    def __init__(self, log, s, n_parallel, owner, cmd):
        self._log = log
        self._s = s
        self.n_parallel = n_parallel
        self.owner = owner
        self.cmd = cmd
        self.__workers = {}  # map from Popen to log index
        self.ch2 = self.__get_ch2()
        self.clear_all()

    def __get_ch2(self):
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
            self._log.debug(f'Using command "{ch2}"')
            return ch2

    def clear_all(self):
        for worker in self.__workers.keys():
            self._log.warning(f'Killing pending PID {worker.pid} ({worker.args})')
            worker.kill()
            self._delete_pid(worker.pid)
        for process in self._s.query(SystemProcess). \
                filter(SystemProcess.owner == self.owner).all():
            if pid_exists(process.pid):
                p = Process(process.pid)
                if abs(p.create_time() - process.start) < DELTA_TIME:
                    self._log.warning(f'Killing rogue PID {process.pid} ({" ".join(p.cmdline())})')
                    p.kill()
            self._s.delete(process)
        self._s.commit()

    def _delete_pid(self, pid):
        self._s.query(SystemProcess). \
            filter(SystemProcess.owner == self.owner,
                   SystemProcess.pid == pid).delete()

    def _read_pid(self, pid):
        return self._s.query(SystemProcess). \
            filter(SystemProcess.owner == self.owner,
                   SystemProcess.pid == pid).one()

    def run(self, args):
        self.wait(self.n_parallel - 1)
        log_index = self._free_log_index()
        log = f'{short_cls(self.owner)}.{log_index}.{LOG}'
        cmd = (self.cmd + ' ' + args).format(log=log, ch2=self.ch2)
        worker = Popen(args=cmd, shell=True)
        self._log.debug(f'Adding command "{cmd}"')
        self._s.add(SystemProcess(command=cmd, owner=self.owner, pid=worker.pid, log=log))
        self.__workers[worker] = log_index

    def wait(self, n_workers=0):
        # import pdb; pdb.set_trace()
        while len(self.__workers) > n_workers:
            for worker in self.__workers:
                worker.poll()
                process = self._read_pid(worker.pid)
                if worker.returncode is not None:
                    try:
                        del self.__workers[worker]
                        if worker.returncode:
                            raise Exception(f'Worker "{process.command}" exited with return code {worker.returncode} '
                                            f'see {process.log} for more info')
                        else:
                            return
                    finally:
                        self._delete_pid(worker.pid)
                        if worker.returncode:
                            self.clear_all()
            sleep(SLEEP)

    def _substitutions(self, log_index):
        like = short_cls(self.owner)
        log = like + '.' + str(log_index)
        return {LOG: log, LIKE: like}

    def _free_log_index(self):
        used = set(self.__workers.values())
        for i in range(self.n_parallel):
            if i not in used:
                return i
        raise Exception('No log available (too many workers)')
