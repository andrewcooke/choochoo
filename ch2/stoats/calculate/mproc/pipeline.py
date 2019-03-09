
from abc import abstractmethod

from .worker import Workers
from .. import Statistics
from ....command.args import WORKER, FORCE
from ....squeal.types import short_cls

N_CPU = 'n_cpu'


class MultiProcStatistics(Statistics):

    def __init__(self, *args, overhead=1, cost_calc=1, cost_write=1, **kargs):
        super().__init__(*args, **kargs)
        self.overhead = overhead
        self.cost_calc = cost_calc
        self.cost_write = cost_write

    def run(self):

        worker = self._karg(WORKER, default=False)
        force = self._karg(FORCE, default=False)
        n_cpu = self._karg(N_CPU, default=1)

        if force:
            if worker:
                self._log.warning('Worker deleting data')
            self._delete()

        missing = self._missing()
        if worker:
            self._run_all(missing)
        elif not missing:
            self._log.info(f'No missing statistics for {short_cls(self)}')
        else:
            n_total, n_parallel = self.__cost_benefit(missing, n_cpu)
            if n_total < 2:
                self._run_all(missing)
            else:
                self.__spawn(missing, n_total, n_parallel)

    @abstractmethod
    def _missing(self):
        raise NotImplementedError()

    @abstractmethod
    def _run_all(self, missing):
        raise NotImplementedError()

    @abstractmethod
    def _delete(self):
        raise NotImplementedError()

    def __cost_benefit(self, missing, n_cpu):

        # is it worth using workers?  there's some cost in starting them up and there will be contention
        # in accessing the database.
        # let's say COST (for one missing time) is COST_WRITE + COST_CALC (ignoring units).
        # if we have N_MISSING tasks divided into N_TOTAL workloads amongst N_PARALLEL workers
        # then we have these conditions:
        # 1: N_PARALLEL * (COST_WRITES/ COST) <= 1 so that we avoid blocking completely on writes
        # 2: (N_MISSING / N_TOTAL) * COST > OVERHEAD so we're not wasting our time
        # 3: N_PARALLEL <= N_CPU
        # 4: N_TOTAL <= N_MISSING

        self._log.debug(f'Batching for n_cpu={n_cpu}, overhead={self.overhead}, '
                        f'cost_writes={self.cost_write} cost_calc={self.cost_calc}')
        n_missing = len(missing)
        cost = self.cost_write + self.cost_calc
        limit_1 = cost / self.cost_write
        self._log.debug(f'Limit on parallel workers from database contention is {limit_1:3.1f}')
        limit_2 = cost * n_missing / self.overhead
        self._log.debug(f'Limit on total workers from overhead is {limit_2:3.1f}')
        limit_3 = n_cpu
        self._log.debug(f'Limit on parallel workers from CPU count is {limit_3:d}')
        limit_4 = n_missing
        self._log.debug(f'Limit on total workers from work available is {limit_4:d}')
        n_total = int(min(limit_2, limit_4))
        n_parallel = int(min(limit_1, limit_3, n_total))
        return n_total, n_parallel

    def __spawn(self, missing, n_total, n_parallel):

        # unfortunately we have to do things with contiguous dates, which may introduce systematic
        # errors in our timing estimates

        n_missing = len(missing)
        workers = Workers(self._log, self._db.session(), n_parallel, self)
        start, finish = None, -1
        for i in range(n_total):
            start = finish + 1
            finish = int(0.5 + (i+1) * (n_missing-1) / n_total)
            if start > finish: raise Exception('Bad chunking logic')
            self._new_worker(missing[start], missing[finish], workers)
        workers.wait()

    @abstractmethod
    def _new_worker(self, start, finish, workers):
        raise NotImplementedError()
