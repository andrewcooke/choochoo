
from abc import abstractmethod
from logging import getLogger

from sqlalchemy.sql.functions import count

from .loader import Loader
from ..commands.args import LOG, WORKER, DEV, PROCESS, FORCE
from ..common.args import mm
from ..common.global_ import global_dev
from ..common.names import BASE
from ..common.names import VERBOSITY, URI
from ..lib.utils import timing
from ..lib.workers import ProgressTree, command_root
from ..sql import Pipeline, Interval, PipelineType, StatisticJournal
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

    def __init__(self, config, *args, owner_out=None, force=False, progress=None, worker=None, id=None, **kargs):
        self._config = config
        self.owner_out = owner_out or self  # the future owner of any calculated statistics
        self.force = force  # force re-processing
        self._progress = progress
        self.worker = worker
        self.id = id
        dev = mm(DEV) if global_dev() else ''
        self.__ch2 = f'{command_root()} {mm(BASE)} {config.args[BASE]} {dev} {mm(VERBOSITY)} 0'
        super().__init__(*args, **kargs)

    def missing(self):
        with self._config.db.session_context(expire_on_commit=False) as s:
            self._startup(s)
        if self.force:
            with self._config.db.session_context() as s:
                log.warning(f'Deleting data for {short_cls(self.__class__)}')
                self._delete(s)
        with self._config.db.session_context(expire_on_commit=False) as s:
            return self._missing(s)
        # no shutdown - that's only after actually doing something

    def run(self):
        with self._config.db.session_context(expire_on_commit=False) as s:
            self._startup(s)
        if not self.worker and self.force:
            with self._config.db.session_context() as s:
                self._delete(s)
        with self._config.db.session_context(expire_on_commit=False) as s:
            missing = self._missing(s)
        self._recalculate(self._config.db, missing)
        with self._config.db.session_context() as s:
            self._shutdown(s)

    def _startup(self, s):
        pass

    def command_for_missing(self, pipeline, missing, log_name):
        from .process import fmt_cmd
        force = ' ' + mm(FORCE) if self.force else ''
        cmd = self.__ch2 + f' {mm(LOG)} {log_name} {mm(URI)} {self._config.args._format(URI)} ' \
                           f'{PROCESS}{force} {mm(WORKER)} {pipeline.id} {self.format_missing(missing)}'
        log.debug(fmt_cmd(cmd))
        return cmd

    def format_missing(self, missing):
        return " ".join(str(m) for m in missing)

    @abstractmethod
    def _delete(self, s):
        raise NotImplementedError('_delete')

    @abstractmethod
    def _missing(self, s):
        raise NotImplementedError('_missing')

    @abstractmethod
    def _recalculate(self, db, missing):
        raise NotImplementedError('_recalculate')

    def _shutdown(self, s):
        pass

    def _recalculate(self, db, missing):
        local_progress = ProgressTree(len(missing), parent=self._progress)
        if not missing:
            log.info(f'No missing data for {short_cls(self)}')
            local_progress.complete()
        else:
            for missed in missing:
                with local_progress.increment_or_complete():
                    with db.session_context() as s:
                        self._run_one(s, missed)

    @abstractmethod
    def _run_one(self, s, missed):
        raise NotImplementedError()


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
