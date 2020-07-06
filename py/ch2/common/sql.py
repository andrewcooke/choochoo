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

    def __init__(self, args, factory, db_version, env_prefix):
        self.__env_prefix = env_prefix
        self.__fmt_keys = {BASE: self.__read(args, BASE),
                           USER: self.__read(args, USER),
                           PASSWD: self.__read(args, PASSWD),
                           VERSION: db_version}
        self.__base = self.__fmt_keys[BASE]  # still needed to import from sqlite
        self.__uri = self.__read(args, URI)
        self.__factory = factory
        self.__db = None

    def __read(self, args, name):
        '''Environment overrides command line so that system config overrides user preferences.'''
        env_name = self.__env_prefix + name.upper()
        if env_name in environ:
            value = environ[env_name]
            log.debug(f'{name}={value} (from {env_name})')
        else:
            value = args[name]
            if name == PASSWD:
                log.debug(f'{name}=xxxxxx (from args)')
            else:
                log.debug(f'{name}={value} (from args)')
        return value

    @property
    def base(self):
        return self.__base

    @property
    def db(self):
        if not self.__db:
            self.__db = self.get_database()
        return self.__db

    def reset(self):
        self.__db = None

    def get_safe_uri(self, uri=None, **kwargs):
        keys = dict(kwargs)
        keys[PASSWD] = 'xxxxxx'
        return self.get_uri(uri=uri, **keys)

    def get_uri(self, uri=None, **kwargs):
        if not uri: uri = self.__uri
        keys = dict(self.__fmt_keys)
        keys.update(**kwargs)
        return uri.format(**keys)

    def get_database(self, uri=None, **kwargs):
        safe_uri = self.get_safe_uri(uri=uri, **kwargs)
        log.debug(f'Connecting to {safe_uri}')
        uri = self.get_uri(uri=uri, **kwargs)
        return self.__factory(uri)
