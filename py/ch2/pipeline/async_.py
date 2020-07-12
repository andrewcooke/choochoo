from asyncio import create_subprocess_shell, wait, FIRST_COMPLETED, get_event_loop
from multiprocessing import cpu_count

from ..lib.workers import ProgressTree
from ..sql import PipelineType, Interval, Pipeline


def run_pipeline(config, type, like=tuple(), progress=None, worker=None, **extra_kargs):
    if type in (PipelineType.CALCULATE, PipelineType.READ_ACTIVITY, PipelineType.READ_MONITOR):
        async_run_pipeline(config, type, like=like, progress=progress, worker=worker, **extra_kargs)
    else:
        from .pipeline import run_pipeline
        run_pipeline(config, type, like=like, progress=progress, worker=worker, **extra_kargs)


def async_run_pipeline(config, type, like=tuple(), progress=None, worker=None, **extra_kargs):
    if not worker:
        with config.db.session_context() as s:
            Interval.clean(s)
    with config.db.session_context(expire_on_commit=False):
        pipelines = Pipeline.all(s, type, like=like, id=worker)
    AsyncRunner(config, pipelines, worker=worker, **extra_kargs).run(progress)


def instantiate_pipeline(pipeline, config, kargs):
    return pipeline.cls(config, **kargs)


class AsyncRunner:

    def __init__(self, config, pipeline_classes, worker=None, n_cpu=cpu_count(), load=0.9, **kargs):
        if worker and len(pipeline_classes) > 1: raise Exception('Worker with multiple pipelines')
        if not pipeline_classes: raise Exception('No pipelines')
        self.__config = config
        self.__pipeline_classes = pipeline_classes
        self.__worker = worker
        self.__n_cpu = n_cpu
        self.__load = load
        self.__kargs = kargs

    def run(self, progress):
        local_progress = ProgressTree(len(self.__pipeline_classes), parent=progress)
        if self.__worker:
            if len(self.__pipeline_classes) > 1: raise Exception(f'Worker with multiple classes {self.__worker}')
            self.__run_local(local_progress, self.__pipeline_classes[0])
        else:
            self.__run_commands(local_progress,
                                DependencyQueue([cls() for cls in self.__pipeline_classes], self.__kargs))

    def __run_local(self, local_progress, pipeline):
        instance = instantiate_pipeline(pipeline, self.__config, self.__kargs)
        with local_progress.increment_or_complete():
            instance.run()

    def __run_commands(self, local_progress, queue):
        capacity = max(1, int(self.__n_cpu * self.__load))
        pipelines, processes = {}, []
        loop = get_event_loop()
        try:
            with self.__config.db.session_context() as s:
                try:
                    while True:
                        pipeline, cmd = queue.pop(s)
                        process = create_subprocess_shell(cmd)
                        pipelines[process] = pipeline
                        processes.append(process)
                        if len(processes) == capacity:
                            processes = self._run_til_next(loop, pipelines, processes, queue, local_progress)
                except EmptyException:
                    while processes:
                        processes = self._run_til_next(loop, pipelines, processes, queue)
        finally:
            local_progress.complete()

    def _run_til_next(self, loop, pipelines, processes, queue, local_progress):
        done, remain = loop.run_until_complete(wait(processes, return_when=FIRST_COMPLETED))
        for process in done:
            queue.complete(pipelines.pop(process.result()))
            local_progress.increment(1)
        return [process.result() for process in remain]


class EmptyException(Exception): pass


class DependencyQueue:

    def __init__(self, config, pipelines, kargs):
        self.__config = config
        self.__blocked = [pipeline for pipeline in pipelines if pipeline.blocked_by]
        self.__unblocked = [pipeline for pipeline in pipelines if not pipeline.blocked_by]
        self.__complete = []
        self.__active = []  # (pipeline, instances)
        self.__active_count = {}  # pipeline: count
        self.__kargs = kargs

    def complete(self, pipeline):
        # check if completed instance means that a pipeline is complete and, if so,
        # see if that unblocks others
        self.__active_count[pipeline] -= 1
        if not self.__active_count[pipeline]:
            del self.__active_count[pipeline]
            self.__complete.append(pipeline)
            for i in reversed(range(len(self.__blocked))):
                if all(blocker in self.__complete for blocker in self.__blocked[i]):
                    self.__unblocked.append(self.__blocked.pop(i))

    def pop(self, s):
        # unblocking takes some time, so do it step by step as we need more
        # add the new pipeline to the head of active
        if self.__unblocked:
            pipeline = self.__unblocked.pop()
            instance = instantiate_pipeline(pipeline, self.__config, self.__kargs)
            missing = instance.missing()
            self.__active.insert(0, (pipeline, missing))
            self.__active_count[pipeline] = 0
        # take the head of active, remove an instance, and rotate
        try:
            (pipeline, instance, missing) = self.__active.pop(0)
            cmd = instance.command_for_missing(missing.pop())
            self.__active_count[pipeline] += 1
            if missing:
                self.__active.append((pipeline, instance, missing))
            return pipeline, cmd
        except IndexError:
            raise EmptyException()


