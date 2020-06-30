from re import sub
from typing import Mapping

from .names import BIND, PORT


class NamespaceWithVariables(Mapping):

    def __init__(self, ns):
        self._dict = vars(ns)

    def __getitem__(self, name):
        try:
            value = self._dict[name]
        except KeyError:
            value = self._dict[sub('-', '_', name)]
        return value

    def __iter__(self):
        return iter(self._dict)

    def __len__(self):
        return len(self.__dict__)


def mm(name): return '--' + name


def m(name): return '-' + name


def no(name): return 'no-%s' % name


def add_web_server_args(cmd, prefix='', default_address='localhost', default_port=80):
    if prefix: prefix += '-'
    cmd.add_argument(mm(prefix + BIND), default='localhost', metavar='ADDRESS',
                     help='bind address' + f' (default {default_address})' if default_address else '')
    cmd.add_argument(mm(prefix + PORT), default=default_port, type=int, metavar='PORT',
                     help=f'port' + f' (default {default_port})' if default_port else '')

