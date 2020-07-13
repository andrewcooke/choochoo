from logging import getLogger

from .names import VERSION, URI

log = getLogger(__name__)


class BaseConfig:

    def __init__(self, args, factory, db_version):
        self.args = args
        self.args[VERSION] = db_version
        self.__factory = factory
        self.__db = None

    @property
    def db(self):
        if not self.__db:
            self.__db = self.get_database()
        return self.__db

    def reset(self):
        self.__db = None

    def get_database(self, **kargs):
        # prefer kargs to _with so that passwd is not displayed
        args = self.args._with(**kargs)
        safe_uri = args._with(passwd='xxxxxx')._format(URI)
        log.debug(f'Connecting to {safe_uri}')
        uri = args._format(URI)
        return self.__factory(uri)

    def _with(self, **kargs):
        # may need to be over-written by subclasses
        args = self.args._with(**kargs)
        return BaseConfig(args, self.__factory, args[VERSION])

