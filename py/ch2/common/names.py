from re import sub, ASCII

from .date import to_time

ADMIN_USER = 'admin-user'
ADMIN_PASSWD = 'admin-passwd'
BASE = 'base'
BIND = 'bind'
COLOR = 'color'
COLOUR = 'colour'
COMMAND = 'command'
DARK = 'dark'
DB = 'db'
L = 'l'
LIGHT = 'light'
LIST = 'list'
OFF = 'off'
P = 'p'
PASSWD = 'passwd'
PORT = 'port'
POSTGRESQL = 'postgresql'
PREVIOUS = 'previous'
SQLITE = 'sqlite'
U = 'u'
URI = 'uri'
USER = 'user'
V = 'v'
VERBOSITY = 'verbosity'
VERSION = 'version'
WEB = 'web'

UNDEF = object()
TIME_ZERO = to_time(0.0)


def assert_name(name, extended=False):
    if not valid_name(name, extended=extended):
        raise Exception(f'Bad name: {name}')
    return name


def valid_name(name, extended=False):
    # this relies on '_' not being a valid identifier to exclude various system tables
    if extended:
        clean = sub(r'[^-A-Za-z0-9:]', '', name, flags=ASCII)
    else:
        clean = sub(r'[^-A-Za-z0-9]', '', name, flags=ASCII)
    if clean != name: return False
    if name.startswith('template'): return False
    if name in ('postgres', 'admin', 'public'): return False
    return True
