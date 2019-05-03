
from abc import abstractmethod
from logging import getLogger
from time import time

from psutil import cpu_count

from .load import StatisticJournalLoader
from ..lib.date import format_seconds
from ..lib.utils import short_str
from ..lib.workers import Workers
from ..squeal import Pipeline
from ..squeal.types import short_cls

log = getLogger(__name__)
CPU_FRACTION = 0.9
MAX_REPEAT = 3
NONE = object()


def run_pipeline(db, type, like=None, id=None, **extra_kargs):
    with db.session_context() as s:
        for pipeline in Pipeline.all(s, type, like=like, id=id):
            kargs = dict(pipeline.kargs)
            kargs.update(extra_kargs)
            log.info(f'Running {short_cls(pipeline.cls)}({short_str(pipeline.args)}, {short_str(kargs)}')
            log.debug(f'Running {pipeline.cls}({pipeline.args}, {kargs})')
            start = time()
            pipeline.cls(db, *pipeline.args, id=pipeline.id, **kargs).run()
            duration = time() - start
            log.info(f'Ran {short_cls(pipeline.cls)} in {format_seconds(duration)}')


class BasePipeline:

    def __init__(self, *args, **kargs):
        if args or kargs:
            log.warning(f'Unused ({type(self)}): {args} {list(kargs.keys())}')

    def _assert(self, name, value):
        if value is None:
            raise Exception(f'Undefined {name}')
        else:
            return value


class MultiProcPipeline(BasePipeline):

    def __init__(self, db, *args, owner_out=None, force=False,
                 overhead=1, cost_calc=20, cost_write=1, n_cpu=None, worker=None, id=None, **kargs):
        self._db = db
        self.owner_out = owner_out or self  # the future owner of any calculated statistics
        self.force = force  # force re-processing
        self.overhead = overhead  # next three args are used to decide if workers are needed
        self.cost_calc = cost_calc  # see _cost_benefit for full details
        self.cost_write = cost_write  # defaults guarantee a single thread
        self.n_cpu = max(1, int(cpu_count() * CPU_FRACTION)) if n_cpu is None else n_cpu  # number of cpus available
        self.worker = worker  # if True, then we're in a sub-process
        self.id = id  # the id for the pipeline entry in the database (passed to sub-processes)
        super().__init__(*args, **kargs)

    def run(self):
        with self._db.session_context() as s:
            self._startup(s)

            if self.force:
                if self.worker:
                    log.warning('Worker deleting data')
                self._delete(s)

            missing = self._missing(s)
            log.debug(f'Have {len(missing)} missing ranges')

            if self.worker:
                log.debug('Worker, so execute directly')
                self._run_all(s, missing)
            elif not missing:
                log.info(f'No missing data for {short_cls(self)}')
            else:
                n_total, n_parallel = self.__cost_benefit(missing, self.n_cpu)
                if n_parallel < 2 or len(missing) == 1:
                    self._run_all(s, missing)
                else:
                    self.__spawn(s, missing, n_total, n_parallel)
            self._shutdown(s)

    def _run_all(self, s, missing):
        for missed in missing:
            log.debug(f'Run {missed}')
            self._run_one(s, missed)
            s.commit()

    def _startup(self, s):
        pass

    def _shutdown(self, s):
        pass

    # as a general rule, _missing and _args should be implemented together
    @abstractmethod
    def _missing(self, s):
        raise NotImplementedError()

    @abstractmethod
    def _delete(self, s):
        raise NotImplementedError()

    @abstractmethod
    def _run_one(self, s, missed):
        raise NotImplementedError()

    def __cost_benefit(self, missing, n_cpu):

        # is it worth using workers?  there's some cost in starting them up and there will be contention
        # in accessing the database.
        # let's say COST (for one missing time) is COST_WRITE + COST_CALC (ignoring units).
        # if we have N_MISSING tasks divided into N_TOTAL workloads amongst N_PARALLEL workers
        # then we have these conditions (in order):
        #   N_PARALLEL * (COST_WRITES/ COST) <= 1 so that we avoid blocking completely on writes
        #   N_PARALLEL <= N_CPU
        #   N_TOTAL <= N_MISSING / N_PARALLEL
        #   (N_MISSING / N_TOTAL) * COST > OVERHEAD so we're not wasting our time
        #   N_TOTAL <= N_PARALLEL * MAX_REPEAT because we want large batches, but not too large
        # really we should include estimates of disk and cpu speed here, in which case we need to separate
        # out COST_READ too (currently folded into COST_CALC).

        log.debug(f'Batching for n_cpu={n_cpu}, overhead={self.overhead}, '
                  f'cost_writes={self.cost_write}, cost_calc={self.cost_calc}')
        n_missing = len(missing)
        cost = self.cost_write + self.cost_calc
        limit = cost / self.cost_write
        log.debug(f'Limit on parallel workers from database contention is {limit:3.1f}')
        log.debug(f'Limit on parallel workers from CPU count is {n_cpu:d}')
        n_parallel = int(min(limit, n_cpu))
        n_total = int((n_missing + n_parallel - 1) / n_parallel)
        log.debug(f'Limit on total workers from work available is {n_total:d}')
        limit = cost * n_missing / self.overhead
        log.debug(f'Limit on total workers from overhead is {limit:3.1f}')
        n_total = min(n_total, int(limit))
        limit = n_parallel * MAX_REPEAT
        log.debug(f'Limit on total workers to boost batch size is {limit:d}')
        n_total = min(n_total, limit)
        log.info(f'Threads: {n_total}/{n_parallel}')
        return n_total, n_parallel

    def __spawn(self, s, missing, n_total, n_parallel):

        # unfortunately we have to do things with contiguous dates, which may introduce systematic
        # errors in our timing estimates

        n_missing = len(missing)
        workers = Workers(s, n_parallel, self.owner_out, self._base_command())
        start, finish = None, -1
        for i in range(n_total):
            start = finish + 1
            finish = int(0.5 + (i+1) * (n_missing-1) / n_total)
            if start > finish: raise Exception('Bad chunking logic')
            workers.run(self._args(missing, start, finish))
        workers.wait()

    # as a general rule, _missing and _args should be implemented together
    @abstractmethod
    def _args(self, missing, start, finish):
        raise NotImplementedError()

    @abstractmethod
    def _base_command(self):
        raise NotImplementedError()


class UniProcPipeline(MultiProcPipeline):

    def __init__(self, *args, overhead=None, cost_calc=None, cost_write=None, n_cpu=None, worker=None, id=None,
                 **kargs):
        super().__init__(*args, overhead=1, cost_calc=0, cost_write=1, n_cpu=None, worker=None, id=None, **kargs)


class LoaderMixin:

    def _get_loader(self, s, **kargs):
        if 'owner' not in kargs:
            kargs['owner'] = self.owner_out
        return StatisticJournalLoader(s, **kargs)
