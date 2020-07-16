from collections import defaultdict
from logging import getLogger
from multiprocessing import cpu_count
from time import sleep

from ..commands.args import LOG
from ..lib.workers import ProgressTree
from ..sql import PipelineType, Interval, Pipeline
from ..sql.types import short_cls

log = getLogger(__name__)


def run_pipeline(config, type, like=tuple(), progress=None, worker=None, **extra_kargs):
    if type is None or type in (PipelineType.CALCULATE, PipelineType.READ_ACTIVITY, PipelineType.READ_MONITOR):
        mproc_run_pipeline(config, type, like=like, progress=progress, worker=worker, **extra_kargs)
    else:
        from .pipeline import run_pipeline
        run_pipeline(config, type, like=like, progress=progress, worker=worker, **extra_kargs)


def mproc_run_pipeline(config, type, like=tuple(), progress=None, worker=None, **extra_kargs):
    if not worker:
        with config.db.session_context() as s:
            Interval.clean(s)
    with config.db.session_context(expire_on_commit=False) as s:
        pipelines = list(Pipeline.all(s, type, like=like, id=worker, eager=True))
    ProcessRunner(config, pipelines, worker=worker, **extra_kargs).run(progress)


def instantiate_pipeline(pipeline, config, kargs):
    log.debug(f'Instantiating {short_cls(pipeline.cls)} with {kargs}')
    kargs = dict(kargs)
    kargs.update(pipeline.kargs)
    return pipeline.cls(config, **kargs)


class ProcessRunner:

    def __init__(self, config, pipelines, worker=None, n_cpu=cpu_count(), load=0.9, **kargs):
        if worker and len(pipelines) > 1: raise Exception('Worker with multiple pipelines')
        if not pipelines: raise Exception('No pipelines')
        self.__config = config
        self.__pipelines = pipelines
        self.__worker = worker
        self.__n_cpu = n_cpu
        self.__load = load
        self.__kargs = kargs

    def run(self, progress):
        local_progress = ProgressTree(len(self.__pipelines), parent=progress)
        if self.__worker or self.__n_cpu == 1:
            if self.__worker and len(self.__pipelines) > 1:
                raise Exception(f'Worker with multiple classes {self.__worker}')
            for pipeline in self.__pipelines:
                self.__run_local(local_progress, pipeline)
        else:
            self.__run_commands(local_progress, DependencyQueue(self.__config, self.__pipelines, self.__kargs))

    def __run_local(self, local_progress, pipeline):
        log.info(f'Running pipeline {short_cls(pipeline.cls)} locally with {self.__kargs}')
        instance = instantiate_pipeline(pipeline, self.__config, self.__kargs)
        with local_progress.increment_or_complete():
            instance.run()

    def __run_commands(self, local_progress, queue):
        log.info('Scheduling worker pipelines')
        capacity = max(1, int(self.__n_cpu * self.__load))
        pipelines, popens = {}, []
        try:
            with self.__config.db.session_context() as s:
                try:
                    while True:
                        pipeline, cmd, log_index = queue.pop()
                        log.debug(f'Preparing worker for {short_cls(pipeline.cls)}')
                        popen = self.__config.run_process(pipeline.cls, cmd, log_name(pipeline, log_index))
                        log.debug(f'Created subprocess {popen}')
                        pipelines[popen] = (pipeline, log_index)
                        popens.append(popen)
                        if len(popens) == capacity:
                            popens = self._run_til_next(pipelines, popens, queue)
                except EmptyException:
                    while popens:
                        popens = self._run_til_next(pipelines, popens, queue)
        finally:
            local_progress.complete()

    def _run_til_next(self, pipelines, popens, queue):
        queue.log()
        log.debug('Waiting for a subprocess to complete')
        while True:
            for i, popen in enumerate(popens):
                popen.poll()
                process = self.__config.get_process(pipelines[popen][0].cls, popen.pid)
                if popen.returncode is not None:
                    pipeline, log_index = pipelines.pop(popen)
                    queue.complete(pipeline, log_index)
                    if popen.returncode:
                        msg = f'Command "{popen.args}" exited with return code {popen.returncode} ' + \
                              f'see {process.log} for more info'
                        log.warning(msg)
                        self._abort(pipelines, popens)
                        raise Exception(msg)
                    else:
                        log.debug(f'Command "{popen.args}" finished successfully')
                        self.__config.delete_process(pipeline.cls, popen.pid)
                        del popens[i]
                        return popens
            sleep(0.1)

    def _abort(self, pipelines, popens):
        for popen in popens:
            log.warning(f'Killing PID {popen.pid} ({popen.args})')
            popen.kill()
            pipeline, log_index = pipelines[popen]
            self.__config.delete_process(pipeline.cls, popen.pid)


class EmptyException(Exception): pass


class DependencyQueue:

    def __init__(self, config, pipelines, kargs):
        self.__config = config
        self.__blocked = [pipeline for pipeline in pipelines if pipeline.blocked_by]
        self.__unblocked = [pipeline for pipeline in pipelines if not pipeline.blocked_by]
        self.__complete = []
        self.__active = {}  # pipeline: (instance, missing)
        self.__stats = {}  # pipeline: Stats
        self.__order = []
        self.__kargs = kargs
        self.__active_log_indices = defaultdict(lambda: set())

    def complete(self, pipeline, log_index):
        # check if completed instance means that a pipeline is complete and, if so,
        # see if that unblocks others
        self.__stats[pipeline].finish()
        self.__active_log_indices[pipeline].remove(log_index)
        if self.__stats[pipeline]:
            self.__complete.append(pipeline)
            for i in reversed(range(len(self.__blocked))):
                if all(blocker in self.__complete for blocker in self.__blocked[i]):
                    self.__unblocked.append(self.__blocked.pop(i))

    def pop(self):
        # unblocking takes some time, so do it step by step as we need more
        # add the new pipeline to the head of active
        if self.__unblocked:
            pipeline = self.__unblocked.pop()
            instance = instantiate_pipeline(pipeline, self.__config, self.__kargs)
            missing = instance.missing()
            self.__active[pipeline] = (instance, missing)
            self.__order.insert(0, pipeline)
            self.__stats[pipeline] = Stats(pipeline, missing)
        try:
            pipeline = self.__order.pop(0)
            instance, missing = self.__active[pipeline]
            log_index = self.__unused_log_index(pipeline)
            cmd = instance.command_for_missing(pipeline, missing.pop(), log_name(pipeline, log_index))
            if missing:
                self.__order.append(pipeline)
            else:
                del self.__active[pipeline]
            self.__stats[pipeline].start()
            return pipeline, cmd, log_index
        except IndexError:
            raise EmptyException()

    def __unused_log_index(self, pipeline):
        index = 0
        while index in self.__active_log_indices[pipeline]: index += 1
        self.__active_log_indices[pipeline].add(index)
        return index

    def log(self):
        for pipeline in self.__stats:
            log.info(str(self.__stats[pipeline]))


class Stats:

    def __init__(self, pipeline, missing):
        self.__name = short_cls(pipeline.cls)
        self.active = 0
        self.total = len(missing)
        self.done = 0

    def start(self):
        self.active += 1

    def finish(self):
        self.active -= 1
        self.done += 1

    def bar(self):
        width = 36
        solid = int(width * self.done / self.total)
        blank = width - solid
        return '-' * blank + '#' * solid

    def __str__(self):
        return f'{self.__name:>20s} {self.active:2d}  {self.done:2d}/{self.total:<2d} {self.bar()}'

    def __bool__(self):
        return self.done == self.total


def log_name(pipeline, log_index):
    return short_cls(pipeline.cls) + '.' + str(log_index) + '.' + LOG
