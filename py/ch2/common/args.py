from logging import getLogger
from os import environ, makedirs
from os.path import exists
from re import sub
from typing import MutableMapping

from .io import clean_path
from .names import BIND, PORT, OFF, LIGHT, DARK, USER, U, PASSWD, P, URI, VERSION, ADMIN_USER, ADMIN_PASSWD

log = getLogger(__name__)


class NamespaceWithVariables(MutableMapping):

    @classmethod
    def _from_ns(cls, ns, env_prefix, version):
        data = vars(ns)
        data[VERSION] = version
        return cls(env_prefix, data)

    def __init__(self, env_prefix, data):
        self.__env_prefix = env_prefix
        self.__dict = {}
        self._set_all(data)

    def _set_all(self, data):
        for name, value in data.items():
            self[name] = value

    def __getitem__(self, name):
        return self.__dict[name]

    def __setitem__(self, name, value):
        value = self.__replace(name, value)
        self.__dict[self.__bar(name)] = value
        self.__dict[self.__unbar(name)] = value

    def __delitem__(self, name):
        del self.__dict[self.__bar(name)]
        del self.__dict[self.__unbar(name)]

    def __iter__(self):
        return iter(self.__dict)

    def __len__(self):
        return len(self.__dict__)

    def _format(self, name=None, value=None):
        if not value: value = self[name]
        while value and '{' in value:
            log.debug(f'Formatting {value}')
            value = value.format(**self)
        return value

    def _format_path(self, name=None, value=None, mkdir=True):
        path = clean_path(self._format(name=name, value=value))
        if not exists(path) and mkdir: makedirs(path, exist_ok=True)
        return path

    def _with(self, **kargs):
        data = dict(self.__dict)
        data.update(kargs)
        return self.__class__(self.__env_prefix, data)

    def __bar(self, name):
        return sub('-', '_', name)

    def __unbar(self, name):
        return sub('_', '-', name)

    def __replace(self, name, value):
        '''Environment overrides command line so that system config overrides user preferences.'''
        env_name = f'{self.__env_prefix}_{self.__bar(name).upper()}'
        if env_name in environ:
            value = environ[env_name]
            log.debug(f'Forcing {name} to {value} via {env_name}')
        return value


def mm(name): return '--' + name


def m(name): return '-' + name


def no(name): return 'no-%s' % name


def add_server_args(cmd, prefix='', default_address='localhost', default_port=80):
    if prefix: prefix += '-'
    cmd.add_argument(mm(prefix + BIND), default='localhost', metavar='ADDRESS',
                     help='bind address' + f' (default {default_address})' if default_address else '')
    cmd.add_argument(mm(prefix + PORT), default=default_port, type=int, metavar='PORT',
                     help=f'port' + f' (default {default_port})' if default_port else '')


def add_data_source_args(parser, uri_default):
    parser.add_argument(mm(USER), m(U), default='default', metavar='USER', help='the current user')
    parser.add_argument(mm(PASSWD), m(P), default='', metavar='PASS', help='user password')
    parser.add_argument(mm(ADMIN_USER), default='postgres', metavar='USER', help='the database admin user')
    parser.add_argument(mm(ADMIN_PASSWD), default='', metavar='PASS', help='user database admin password')
    parser.add_argument(mm(URI), default=uri_default, help='use the given database URI')


def color(color):
    if color.lower() not in (LIGHT, DARK, OFF):
        raise Exception(f'Bad color: {color} ({LIGHT}|{DARK}|{OFF})')
    return color
