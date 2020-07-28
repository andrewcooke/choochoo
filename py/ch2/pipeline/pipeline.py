
from abc import abstractmethod
from logging import getLogger

from sqlalchemy.sql.functions import count

from .loader import Loader
from ..commands.args import LOG, WORKER, DEV, PROCESS, FORCE, CPROFILE
from ..common.args import mm
from ..common.global_ import global_dev
from ..common.names import BASE, UNDEF
from ..common.names import VERBOSITY, URI
from ..lib.utils import timing
from ..lib.workers import ProgressTree, command_root
from ..sql import Pipeline, Interval, PipelineType, StatisticJournal, StatisticName
from ..sql.types import short_cls

log = getLogger(__name__)

CPU_FRACTION = 0.9
MAX_REPEAT = 3


def count_statistics(s):
    return s.query(count(StatisticJournal.id)).scalar()


def run_pipeline(config, type, like=tuple(), progress=None, worker=None, **extra_kargs):
    with config.db.session_context() as s:
        if not worker:
            if type == PipelineType.PROCESS:
                Interval.clean(s)
        local_progress = ProgressTree(Pipeline.count(s, type, like=like, id=worker), parent=progress)
        for pipeline in Pipeline.all(s, type, like=like, id=worker):
            kargs = dict(pipeline.kargs)
            kargs.update(extra_kargs)
            msg = f'Ran {short_cls(pipeline.cls)}'
            if 'activity_group' in kargs: msg += f' ({kargs["activity_group"]})'
            log.debug(f'Running {pipeline}({kargs})')
            with timing(msg):
                before = None if id else count_statistics(s)
                pipeline.cls(config, id=pipeline.id, worker=bool(worker), progress=local_progress, **kargs).run()
                after = None if id else count_statistics(s)
            if before or after:
                log.info(f'{msg}: statistic count {before} -> {after} (change of {after - before})')


class BasePipeline:

    def __init__(self, *args, **kargs):
        if args or kargs:
            log.warning(f'Unused pipeline argument(s) for {short_cls(self)}: {args} {list(kargs.keys())}')

    def _assert(self, name, value):
        if value is None:
            raise Exception(f'Undefined {name}')
        else:
            return value

    @abstractmethod
    def run(self):
        raise NotImplementedError()


class ProcessPipeline(BasePipeline):
    '''
    Can be either called with no arguments except --like and --force, in which case all outstanding data
    are processed, or with --worker id (which identifies the pipeline) and arguments (each of which identifies
    a dataset to process).  In the latter case, --force and --like are ignored.

    When run via ProcessRunner, an instance is created and either:
    * run() is called, in which case all work (worker or not) is done locally.
      in this case, worker should not call startup() and shutdown(), but a "full run" should.
    * startup(), missing(), command_for_missing() (multiple times, invoking worker threads)
      and shutdown() are called in sequence.  The instance is more like a factory in this case.
    In this way startup and shutdown bracket the entire process and are done just once.
    '''

    def __init__(self, config, *args, owner_out=None, force=False, progress=None, worker=None, id=None, cprofile=None,
                 **kargs):
        self.__args = args
        self._config = config
        self.owner_out = owner_out or self  # the future owner of any calculated statistics
        self.force = force  # force re-processing
        self._progress = progress
        self.worker = worker
        self.id = id
        self.cprofile = cprofile
        dev = mm(DEV) if global_dev() else ''
        self.__ch2 = f'{command_root()} {mm(BASE)} {config.args[BASE]} {dev} {mm(VERBOSITY)} 0'
        super().__init__(**kargs)

    def startup(self):
        with self._config.db.session_context(expire_on_commit=False) as s:
            log.debug(f'Starting up {self}')
            self._startup(s)

    def _startup(self, s):
        pass

    def shutdown(self):
        with self._config.db.session_context() as s:
            log.debug(f'Shutting down {self}')
            self._shutdown(s)

    def _shutdown(self, s):
        pass

    def delete(self):
        with self._config.db.session_context() as s:
            log.warning(f'Deleting data for {self}')
            self._delete(s)

    def _delete(self, s):
        raise NotImplementedError('_delete(s)')

    def missing(self):
        '''
        A missing value identities what is to be processed by a worker.  It is typically a file path or
        the start time (local) of an activity.  It is always a string.  It should be quoted if it contains spaces
        or otherwise needs special hanlding by the shell.
        '''
        if self.force:
            self.delete()
        with self._config.db.session_context(expire_on_commit=False) as s:
            missing = self._missing(s) or []  # allow None
        log.debug(f'{len(missing)} missing for {self}')
        return missing

    def _missing(self, s):
        # this should return strings
        raise NotImplementedError('_missing(s)')

    def run(self):
        self.startup()
        if self.worker:
            missing = self.__args
        else:
            missing = [missed.strip('"') for missed in self.missing()]  # will call delete if forced
        local_progress = ProgressTree(len(missing), parent=self._progress)
        try:
            for missed in missing:
                self._run_one(missed)
                local_progress.increment()
            self.shutdown()
        finally:
            local_progress.complete()

    def _run_one(self, missed):
        # this should accept strings
        raise NotImplementedError('_run_one(missed)')

    def command_for_missing(self, pipeline, missing, log_name):
        from .process import fmt_cmd
        force = ' ' + mm(FORCE) if self.force else ''
        cprofile = ''
        if self.cprofile:
            cprofile = ' ' + mm(CPROFILE)
            if self.cprofile[0]:
                cprofile = ' ' + self.cprofile[0]
        cmd = self.__ch2 + f'{cprofile} {mm(LOG)} {log_name} {mm(URI)} {self._config.args._format(URI)} ' \
                           f'{PROCESS}{force} {mm(WORKER)} {pipeline.id} {" ".join(missing)}'
        log.debug(fmt_cmd(cmd))
        return cmd

    def __str__(self):
        return str(short_cls(self.__class__))

    def _provides(self, s, name, type_, units, summary, description, owner=UNDEF, title=None):
        if owner is UNDEF:
            owner = self.owner_out
        StatisticName.add_if_missing(s, name, type_, units, summary, owner, description=description, title=title)


class LoaderMixin:

    def __init__(self, config, *args, batch=True, **kargs):
        super().__init__(config, *args, **kargs)
        self.__batch = batch

    def _get_loader(self, s, add_serial=None, cls=Loader, **kargs):
        if 'owner' not in kargs:
            kargs['owner'] = self.owner_out
        if add_serial is None:
            raise Exception('Select serial use')
        else:
            kargs['add_serial'] = add_serial
        if 'batch' not in kargs:
            kargs['batch'] = self.__batch
            self.__batch = False  # only set once or we get multiple callbacks
        return cls(s, **kargs)


class OwnerInMixin:

    def __init__(self, *args, owner_in=None, **kargs):
        self.owner_in = self._assert('owner_in', owner_in)
        super().__init__(*args, **kargs)
