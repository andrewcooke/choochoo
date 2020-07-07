from logging import getLogger
from os import environ

from sqlalchemy_utils import database_exists

from .log import log_current_exception
from .names import BASE, USER, PASSWD, VERSION, URI

log = getLogger(__name__)


def database_really_exists(uri):
    try:
        return database_exists(uri)
    except Exception:
        log_current_exception(traceback=False)
        return False


class DataSource:

    def __init__(self, args, factory, db_version):
        self.args = args
        self.args[VERSION] = db_version
        self.__factory = factory
        self.__db = None

    @property
    def base(self):
        return self.args[BASE]

    @property
    def db(self):
        if not self.__db:
            self.__db = self.get_database()
        return self.__db

    def reset(self):
        self.__db = None

    def get_safe_uri(self, uri=None, **kargs):
        return self.args._format(name=URI, value=uri, passwd='xxxxxxx', **kargs)

    def get_uri(self, uri=None, **kargs):
        return self.args._format(name=URI, value=uri, **kargs)

    def get_database(self, uri=None, **kwargs):
        safe_uri = self.get_safe_uri(uri=uri, **kwargs)
        log.debug(f'Connecting to {safe_uri}')
        uri = self.get_uri(uri=uri, **kwargs)
        return self.__factory(uri)
