
from subprocess import Popen
from time import sleep

from psutil import pid_exists, Process

from ....squeal import SystemProcess
from ....squeal.types import short_cls

DELTA_TIME = 3
SLEEP = 0.1
LOG = 'log'
LIKE = 'like'


class Workers:

    def __init__(self, log, s, n_parallel, owner):
        self._log = log
        self._s = s
        self.n_parallel = n_parallel
        self.owner = owner
        self.__workers = {}  # map from Popen to log index
        self.clear_all()

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

    def run(self, cmd):
        self.wait(self.n_parallel - 1)
        log_index = self._free_log_index()
        substitutions = self._substitutions(log_index)
        cmd = cmd.format(**substitutions)
        worker = Popen(args=cmd, shell=True)
        self._s.add(SystemProcess(command=cmd, owner=self.owner, pid=worker.pid, log=substitutions[LOG]))
        self.__workers[worker] = log_index

    def wait(self, n_workers=0):
        while len(self.__workers) > n_workers:
            for worker in self.__workers:
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
