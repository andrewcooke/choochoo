
from inspect import getfullargspec
from logging import getLogger
from pkgutil import iter_modules


log = getLogger(__name__)


def read_package(package):
    '''
    This reads files (modules) from a package and extracts functions with the same name as the file.

    That sounds weird, but it's what we want for config and jupyter - see the config.profile and jupyter.template
    packages.

    Note that the file (module) must be imported into __init__ to be visible (more exactly, it must have been
    imported into Python somehow previously).
    '''
    log.debug(f'Reading {package.__file__}')
    log.debug(dir(package))
    for importer, modname, ispkg in iter_modules(package.__path__):
        try:
            module = getattr(package, modname)
            function = getattr(module, modname)
            if hasattr(function, '_original'):
                # drop through template decorator
                argspec = getfullargspec(function._original)
            else:
                argspec = getfullargspec(function)
            yield modname, (function, argspec)
        except AttributeError:
            log.debug(f'Skipping {modname}')
            log.debug('(if this is unexpected, check that the file is imported at the package level)')
