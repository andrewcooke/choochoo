from re import sub
from typing import MutableMapping

from .io import clean_path
from .names import BIND, PORT, OFF, LIGHT, DARK, BASE, USER, U, PASSWD, P, URI


class NamespaceWithVariables(MutableMapping):

    def __init__(self, ns):
        self._dict = dict(vars(ns))

    def __getitem__(self, name):
        try:
            value = self._dict[name]
        except KeyError:
            value = self._dict[sub('-', '_', name)]
        return value

    def __setitem__(self, name, value):
        self._dict[name] = value

    def __delitem__(self, name):
        del self._dict[name]

    def __iter__(self):
        return iter(self._dict)

    def __len__(self):
        return len(self.__dict__)


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
    parser.add_argument(mm(BASE), default='~/.ch2', type=clean_path, metavar='DIR',
                        help='the base directory for data (default ~/.ch2)')
    parser.add_argument(mm(USER), m(U), default='user', metavar='USER', help='the current user')
    parser.add_argument(mm(PASSWD), m(P), default='', metavar='PASS', help='user password')
    parser.add_argument(mm(URI), default=uri_default, help='use the given database URI')


def color(color):
    if color.lower() not in (LIGHT, DARK, OFF):
        raise Exception(f'Bad color: {color} ({LIGHT}|{DARK}|{OFF})')
    return color
