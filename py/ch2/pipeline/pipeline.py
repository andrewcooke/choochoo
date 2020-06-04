
from abc import abstractmethod
from contextlib import nullcontext
from logging import getLogger
from time import time

from psutil import cpu_count
from sqlalchemy import text

from .loader import StatisticJournalLoader
from ..commands.args import SQLITE
from ..lib import format_seconds
from ..lib.workers import ProgressTree, Workers
from ..sql import Pipeline
from ..sql.types import short_cls

log = getLogger(__name__)
CPU_FRACTION = 0.9
MAX_REPEAT = 3
NONE = object()


def run_pipeline(system, db, base, type, like=tuple(), unlike=tuple(), id=None, progress=None, **extra_kargs):
    with db.session_context() as s:
        local_progress = ProgressTree(Pipeline.count(s, type, like=like, unlike=unlike, id=id), parent=progress)
        for pipeline in Pipeline.all(s, type, like=like, unlike=unlike, id=id):
            kargs = dict(pipeline.kargs)
            kargs.update(extra_kargs)
            msg = f'Running {short_cls(pipeline.cls)}'
            if 'activity_group' in kargs: msg += f' ({kargs["activity_group"]})'
            log.info(msg)
            log.debug(f'Running {pipeline.cls}({pipeline.args}, {kargs})')
            start = time()
            pipeline.cls(system, db, *pipeline.args, base=base, id=pipeline.id, progress=local_progress, **kargs).run()
            duration = time() - start
            log.info(f'Ran {short_cls(pipeline.cls)} in {format_seconds(duration)}')


class BasePipeline:

    def __init__(self, *args, **kargs):
        if args or kargs:
            log.warning(f'Unused pipeline argument(s) for {short_cls(self)}: {args} {list(kargs.keys())}')

    def _assert(self, name, value):
        if value is None:
            raise Exception(f'Undefined {name}')
        else:
            return value


class MultiProcPipeline(BasePipeline):

    def __init__(self, system, db, *args, base=None, owner_out=None, force=False, progress=None,
                 overhead=1, cost_calc=20, cost_write=1, n_cpu=None, worker=None, id=None, **kargs):
        self.__system = system
        self.__db = db
        self.base = base
        self.owner_out = owner_out or self  # the future owner of any calculated statistics
        self.force = force  # force re-processing
        self.__progress = progress
        self.overhead = overhead  # next three args are used to decide if workers are needed
        self.cost_calc = cost_calc  # see _cost_benefit for full details
        self.cost_write = cost_write  # defaults guarantee a single thread
        self.n_cpu = max(1, int(cpu_count() * CPU_FRACTION)) if n_cpu is None else n_cpu  # number of cpus available
        self.worker = worker  # if True, then we're in a sub-process
        self.id = id  # the id for the pipeline entry in the database (passed to sub-processes)
        super().__init__(*args, **kargs)

    def run(self):
        with self.__db.session_context() as s:
            self._startup(s)

            if self.force:
                if self.worker:
                    log.warning('Worker deleting data')
                self._delete(s)

            missing = self._missing(s)
            log.debug(f'Have {len(missing)} missing ranges')

            if self.worker:
                log.debug('Worker, so execute directly')
                self._run_all(s, missing, None)
            else:
                local_progress = ProgressTree(len(missing), parent=self.__progress)
                if not missing:
                    log.info(f'No missing data for {short_cls(self)}')
                    local_progress.complete()
                else:
                    self.__flush_wal(s)
                    n_total, n_parallel = self.__cost_benefit(missing, self.n_cpu)
                    if n_parallel < 2 or len(missing) == 1:
                        self._run_all(s, missing, local_progress)
                    else:
                        self.__spawn(s, missing, n_total, n_parallel, local_progress)
            self._shutdown(s)

    def __flush_wal(self, session):
        session.commit()
        if str(session.get_bind().url).startswith(SQLITE):
            log.debug('Clearing WAL')
            session.execute(text('pragma wal_checkpoint(RESTART);'))
            session.commit()
            log.debug('Cleared WAL')

    def _run_all(self, s, missing, progress=None):
        local_progress = progress.increment_or_complete if progress else nullcontext
        for missed in missing:
            with local_progress():
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

    def __spawn(self, s, missing, n_total, n_parallel, progress):

        # unfortunately we have to do things with contiguous dates, which may introduce systematic
        # errors in our timing estimates

        n_missing = len(missing)
        workers = Workers(self.__system, self.base, n_parallel, self.owner_out, self._base_command())
        start, finish = None, -1
        for i in range(n_total):
            start = finish + 1
            finish = int(0.5 + (i+1) * (n_missing-1) / n_total)
            if start > finish: raise Exception('Bad chunking logic')
            with progress.increment_or_complete(finish - start + 1):
                workers.run(self.id, self._args(missing, start, finish))

        workers.wait()

    # as a general rule, _missing and _args should be implemented together
    @abstractmethod
    def _args(self, missing, start, finish):
        raise NotImplementedError()

    @abstractmethod
    def _base_command(self):
        # this should start with the worker ID
        raise NotImplementedError()

    @property
    def db_path(self):
        return self.__db.path


class UniProcPipeline(MultiProcPipeline):

    def __init__(self, *args, overhead=None, cost_calc=None, cost_write=None, n_cpu=None, worker=None, id=None,
                 **kargs):
        super().__init__(*args, overhead=1, cost_calc=0, cost_write=1, n_cpu=None, worker=None, id=None, **kargs)


class LoaderMixin:

    def _get_loader(self, s, add_serial=None, **kargs):
        if 'owner' not in kargs:
            kargs['owner'] = self.owner_out
        if add_serial is None:
            raise Exception('Select serial use')
        else:
            kargs['add_serial'] = add_serial
        return StatisticJournalLoader(s, **kargs)


class OwnerInMixin:

    def __init__(self, *args, owner_in=None, **kargs):
        self.owner_in = self._assert('owner_in', owner_in)
        super().__init__(*args, **kargs)
