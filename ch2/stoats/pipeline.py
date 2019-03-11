
from ..command.args import FORCE, mm, START, FINISH
from ..lib.data import MutableAttr
from ..lib.utils import short_str
from ..squeal import Pipeline
from ..squeal.types import short_cls


NONE = object()


class BasePipeline:

    def __init__(self, log, *args, **kargs):
        self._log = log
        self.__read = set()
        self._on_init(*args, **kargs)

    def _on_init(self, *args, **kargs):
        self._args = args
        self._kargs = MutableAttr(kargs)

    def _karg(self, name, default=NONE):
        if name not in self._kargs:
            if default is NONE:
                raise Exception('Missing %s parameter for %s' % (name, short_cls(self)))
            else:
                self._log.debug(f'Using default for {name}={short_str(default)}')
                self._kargs[name] = default
                self.__read.add(name)  # avoid double logging
        value = self._kargs[name]
        if name not in self.__read:
            self._log.debug(f'{name}={short_str(value)}')
            self.__read.add(name)
        return value

    def _force(self):
        return self._karg(FORCE, default=False)

    def _start_finish(self, type=None):
        start = self._karg(START, default=None)
        finish = self._karg(FINISH, default=None)
        if type:
            if start: start = type(start)
            if finish: finish = type(finish)
        return start, finish


class DbPipeline(BasePipeline):

    def __init__(self, log, db, *args, **kargs):
        self._db = db
        super().__init__(log, *args, **kargs)


def run_pipeline(log, db, type, like=None, id=None, **extra_kargs):
    with db.session_context() as s:
        for pipeline in Pipeline.all(s, type, like=like, id=id):
            kargs = dict(pipeline.kargs)
            kargs.update(extra_kargs)
            log.info(f'Running {short_cls(pipeline.cls)}({short_str(pipeline.args)}, {short_str(kargs)}')
            pipeline.cls(log, db, *pipeline.args, id=pipeline.id, **kargs).run()
