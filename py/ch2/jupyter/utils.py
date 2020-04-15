
from logging import getLogger

from . import template
from ..lib.inspect import read_package

log = getLogger(__name__)


def templates():
    return dict(read_package(template))


def get_template(name):
    return templates()[name]
