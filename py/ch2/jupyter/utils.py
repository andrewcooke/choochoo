from inspect import getfullargspec
from logging import getLogger
from pkgutil import iter_modules

from . import template

log = getLogger(__name__)


def templates():
    log.debug(dir(template))
    log.debug(template.__file__)
    for importer, modname, ispkg in iter_modules(template.__path__):
        try:
            module = getattr(template, modname)
            function = getattr(module, modname)
            argspec = getfullargspec(function._original)
            yield modname, (function, argspec)
        except AttributeError:
            log.debug(f'Skipping {modname}')
            log.debug('(if this is unexpected, check that the template is imported at the package level)')


def get_template(name):
    return dict(templates())[name]
