from collections import defaultdict
from logging import getLogger
from multiprocessing import cpu_count
from time import sleep

from ..commands.args import LOG
from ..common.date import now, format_seconds, time_to_local_time
from ..lib.workers import ProgressTree
from ..sql import PipelineType, Interval, Pipeline

log = getLogger(__name__)


def run_pipeline(config, type, *args, like=tuple(), progress=None, worker=None, **extra_kargs):
    if type is None or type == PipelineType.PROCESS:
        run_process_pipeline(config, type, *args, like=like, progress=progress, worker=worker, **extra_kargs)
    else:
        from .pipeline import run_pipeline
        run_pipeline(config, type, like=like, progress=progress, worker=worker, **extra_kargs)


def run_process_pipeline(config, type, *args, like=tuple(), progress=None, worker=None, **extra_kargs):
    if not worker:
        with config.db.session_context() as s:
            Interval.clean(s)
    with config.db.session_context(expire_on_commit=False) as s:
        pipelines = list(sort_pipelines(Pipeline.all(s, type, like=like, id=worker)))
    ProcessRunner(config, pipelines, *args, worker=worker, **extra_kargs).run(progress)


def instantiate_pipeline(pipeline, config, *args, **kargs):
    kargs = dict(kargs)
    kargs.update(pipeline.kargs)
    log.debug(f'Instantiating {pipeline} with {args}, {kargs}')
    return pipeline.cls(config, *args, **kargs)


class ProcessRunner:

    def __init__(self, config, pipelines, *args, worker=None, n_cpu=cpu_count(), load=1, **kargs):
        if worker and len(pipelines) > 1: raise Exception('Worker with multiple pipelines')
        if not pipelines: raise Exception('No pipelines')
        self.__config = config
        self.__pipelines = pipelines
        self.__worker = worker
        self.__n_cpu = n_cpu
        self.__load = load
        self.__args = args
        self.__kargs = kargs
        self.__max_wait = 0
        self.__max_wait_procs = 0
        self.__max_wait_proc = None

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
        log.info(f'Running pipeline {pipeline} locally with {self.__kargs}')
        instance = instantiate_pipeline(pipeline, self.__config, *self.__args,
                                        id=self.__worker, worker=bool(self.__worker), **self.__kargs)
        with local_progress.increment_or_complete():
            instance.run()

    def __run_commands(self, local_progress, queue):
        log.info('Scheduling worker pipelines')
        capacity = max(1, int(self.__n_cpu * self.__load))
        pipelines, popens = {}, []
        try:
            while True:
                try:
                    pipeline, cmd, log_index = queue.pop()
                    popen = self.__config.run_process(pipeline.cls, cmd, log_name(pipeline, log_index))
                    pipelines[popen] = (pipeline, log_index)
                    popens.append(popen)
                    if len(popens) == capacity:
                        popens = self._run_til_next(pipelines, popens, queue)
                except EmptyException:
                    if popens:
                        log.debug('Nothing new to add')
                        popens = self._run_til_next(pipelines, popens, queue)
                    else:
                        log.debug('Done')
                        queue.shutdown()
                        log.info(f'Maximum wait {format_seconds(self.__max_wait)} for {self.__max_wait_proc} '
                                 f'with {self.__max_wait_procs} processes')
                        return
        finally:
            local_progress.complete()

    def _run_til_next(self, pipelines, popens, queue):
        queue.log()
        start = now()
        log.debug('Waiting for a subprocess to complete')
        while True:
            for i, popen in enumerate(popens):
                popen.poll()
                process = self.__config.get_process(pipelines[popen][0].cls, popen.pid)
                if popen.returncode is not None:
                    duration = (now()- start).total_seconds()
                    log.debug(f'Waited {format_seconds(duration)}')
                    pipeline, log_index = pipelines.pop(popen)
                    if duration > self.__max_wait:
                        self.__max_wait = duration
                        self.__max_wait_procs = len(pipelines) + 1
                        self.__max_wait_proc = str(pipeline)
                    self.__config.delete_process(pipeline.cls, popen.pid)
                    queue.complete(pipeline, log_index)
                    if popen.returncode:
                        msg = f'Command "{popen.args}" exited with return code {popen.returncode} ' + \
                              f'see {process.log} for more info'
                        log.warning(msg)
                        self._abort(pipelines, popens)
                        raise Exception(msg)
                    else:
                        log.debug(f'Command "{fmt_cmd(popen.args)}" finished successfully')
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

    def __init__(self, config, pipelines, kargs, min_missing=1, max_missing=20, gamma=0.4):
        self.__clean_pipelines(pipelines)
        self.__config = config
        self.__blocked = [pipeline for pipeline in pipelines if pipeline.blocked_by]
        self.__unblocked = [pipeline for pipeline in pipelines if not pipeline.blocked_by]
        self.__complete = []
        self.__active = {}  # pipeline: (instance, missing)
        self.__stats = {}  # pipeline: Stats
        self.__order = []
        self.__kargs = kargs
        self.__max_missing = max_missing
        self.__min_missing = min_missing
        self.__gamma = gamma
        self.__active_log_indices = defaultdict(lambda: set())
        self.__start = now()
        # clear out any junk from previous errors?
        for pipeline in self.__unblocked:
            self.__config.delete_all_processes(pipeline.cls)

    def __clean_pipelines(self, pipelines):
        included = set(pipelines)
        for pipeline in pipelines:
            for i in reversed(range(len(pipeline.blocked_by))):
                blocker = pipeline.blocked_by[i]
                if blocker not in included:
                    log.warning(f'Removing {blocker} from blockers for {pipeline}')
                    del pipeline.blocked_by[i]
        log.debug('Cleaned pipelines')

    def complete(self, pipeline, log_index=None):
        # check if completed instance means that a pipeline is complete and, if so,
        # see if that unblocks others
        if log_index is not None:
            self.__stats[pipeline].finish(log_index)
            self.__active_log_indices[pipeline].remove(log_index)
        if self.__stats[pipeline]:
            log.info(f'{pipeline} complete ({self.__stats[pipeline].done})')
            self.__complete.append(pipeline)
            instance, missing = self.__active.pop(pipeline)
            if missing: raise Exception(f'Complete pipeline {pipeline} still has missing values {missing}')
            self.__order = [p for p in self.__order if p != pipeline]
            log.debug(f'Calling shutdown for {pipeline}')
            instance.shutdown()
            for i in reversed(range(len(self.__blocked))):
                if all(blocker in self.__complete for blocker in self.__blocked[i].blocked_by):
                    unblocked = self.__blocked.pop(i)
                    log.info(f'{pipeline} unblocks {unblocked}')
                    self.__unblocked.append(unblocked)
                    self.__config.delete_all_processes(unblocked.cls)

    def pop(self):
        # unblocking takes some time, so do it step by step as we need more
        # add the new pipeline to the head of active
        while self.__unblocked:
            pipeline = self.__unblocked.pop()
            log.debug(f'Making {pipeline} active')
            instance = instantiate_pipeline(pipeline, self.__config, **self.__kargs)
            instance.startup()
            missing = instance.missing()
            self.__stats[pipeline] = Stats(pipeline, missing)
            if missing:
                log.debug(f'{pipeline}: {len(missing)} missing values')
                self.__active[pipeline] = instance, missing
                self.__order.insert(0, pipeline)
                break
            else:
                self.__active[pipeline] = instance, None
                self.__order.insert(0, pipeline)
                self.complete(pipeline)
                log.debug(f'{pipeline}: no missing data')
        for _ in range(len(self.__order)):  # at most, try each once
            pipeline = self.__order.pop(0)
            instance, missing = self.__active[pipeline]
            if missing:
                log_index = self.__unused_log_index(pipeline)
                missing_args, missing = self.__split_missing(pipeline, missing)
                cmd = instance.command_for_missing(pipeline, missing_args, log_name(pipeline, log_index))
                self.__active[pipeline] = instance, missing
                self.__order.append(pipeline)
                log.debug(f'{pipeline}: starting batch of {len(missing_args)} missing values')
                self.__stats[pipeline].start(log_index, len(missing_args))
                return pipeline, cmd, log_index
            else:
                log.debug(f'{pipeline} exhausted')
                self.__active[pipeline] = instance, None
                self.__order.append(pipeline)
        raise EmptyException()

    def __unused_log_index(self, pipeline):
        index = 0
        while index in self.__active_log_indices[pipeline]: index += 1
        self.__active_log_indices[pipeline].add(index)
        return index

    def log(self):
        log.info(f'Started {time_to_local_time(self.__start)}; '
                 f'duration {format_seconds((now() - self.__start).total_seconds())}')
        for pipeline in self.__stats:
            log.info(str(self.__stats[pipeline]))

    def __log_efficiency(self):
        clock_time = (now() - self.__start).total_seconds()
        process_time = 0
        for pipeline in self.__stats:
            process_time += self.__stats[pipeline].duration_individual
        speedup = process_time / clock_time
        log.info(f'Clock time: {format_seconds(clock_time)}; Process time: {format_seconds(process_time)}; '
                 f'Speedup: x{speedup:.1f}')
        log.info(f'Missing args min {self.__min_missing}; max {self.__max_missing}; gamms {self.__gamma}')

    def __split_missing(self, pipeline, missing):
        # this (min, min) is a bit weird but makes sense, i think
        lo = min(len(missing), self.__min_missing)
        hi = min(len(missing), self.__max_missing)
        n = max(lo, min(hi, int(pow(self.__stats[pipeline].total, self.__gamma))))
        return missing[:n], missing[n:]

    def shutdown(self):
        self.log()
        self.__log_efficiency()
        if self.__blocked:
            log.warning(f'{len(self.__blocked)} pipelines still blocked')
            for pipeline in self.__blocked:
                log.warning(f'{pipeline}: blocked by '
                            f'{", ".join(str(b) for b in pipeline.blocked_by if b not in self.__complete)}')
        else:
            log.debug('All pipelines unblocked')


class Stats:

    def __init__(self, pipeline, missing):
        self.__pipeline = pipeline
        self.active = 0
        self.total = len(missing) if missing else 0
        self.done = 0
        self.duration_overall = 0
        self.duration_individual = 0
        self.__start_overall = now()
        self.__start_individual = {}
        self.__size = {}

    def start(self, index, n):
        self.__start_individual[index] = now()
        self.__size[index] = n
        self.active += 1

    def finish(self, index):
        log.info(f'{self.__pipeline}: {self.__size[index]} completed')
        self.active -= 1
        self.done += self.__size[index]
        self.duration_individual += (now() - self.__start_individual[index]).total_seconds()
        if self:
            self.duration_overall = (now() - self.__start_overall).total_seconds()

    def __bar(self, width):
        solid = int(width * self.done / self.total) if self.total else width
        blank = width - solid
        bar = '-' * blank + '#' * solid
        if self:
            overall_secs = format_seconds(self.duration_overall)
            individual_secs = format_seconds(self.duration_individual)
            secs = f' {overall_secs} / {individual_secs}'
            bar = bar[:-len(secs)] + secs
        return bar

    def __label(self):
        label = str(self.__pipeline)
        for suffix in ('Reader', 'Calculator'):
            if label.endswith(suffix):
                label = label[:-len(suffix)+1] + '%'
        return label

    def __str__(self):
        return f'{self.__label():>13s} {self.__pipeline.id:<2d} {self.active:2d} {self.done:4d}/{self.total:<4d} {self.__bar(40)}'

    def __bool__(self):
        return self.done == self.total


def log_name(pipeline, log_index):
    return f'{pipeline}.{log_index}.{LOG}'


def sort_pipelines(pipelines):
    '''
    not only does this order pipelines so that, if run in order, none is blocked.  it also expands the
    graph so that when the session is disconnected we have all the data we need.
    '''
    included, processed, remaining = set(pipelines), set(), set(pipelines)
    log.debug(f'Sorting {", ".join(str(pipeline) for pipeline in included)}')
    while remaining:
        for pipeline in remaining:
            if all(blocker not in included or blocker in processed for blocker in pipeline.blocked_by):
                yield pipeline
                processed.add(pipeline)
        remaining = remaining.difference(processed)


def fmt_cmd(cmd, max=400):
    if len(cmd) > max:
        n1 = int(0.8 * max)
        n2 = len(cmd) - (max - n1 - 3)
        return cmd[:n1] + '...' + cmd[n2:]
    else:
        return cmd

