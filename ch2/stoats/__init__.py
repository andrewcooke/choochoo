
from ..lib.data import AttrDict
from ..squeal.types import short_cls


class BasePipeline:

    def __init__(self, log, *args, **kargs):
        self._log = log
        self.__read = set()
        self._on_init(*args, **kargs)

    def _on_init(self, *args, **kargs):
        self._args = args
        self._kargs = AttrDict(kargs)

    def _assert_karg(self, name, default=None):
        if name not in self._kargs:
            if default is None:
                raise Exception('Missing %s parameter for %s' % (name, short_cls(self)))
            else:
                self._log.warn('Using default for %s=%s' % (name, default))
                self._kargs[name] = default
        value = self._kargs[name]
        if name not in self.__read:
            self._log.info('%s=%s' % (name, value))
            self.__read.add(name)
        return value


class DbPipeline(BasePipeline):

    def __init__(self, log, db, *args, **kargs):
        self._db = db
        super().__init__(log, *args, **kargs)
