
from inspect import getfullargspec
from logging import getLogger
from pkgutil import iter_modules

from .args import SUB_COMMAND, SERVICE, START, STOP, SHOW, JUPYTER, LIST, PROGNAME, NAME, ARG, STATUS
from ..jupyter import template
from ..jupyter.server import JupyterServer, set_controller, JupyterController

log = getLogger(__name__)


def jupyter(args, system, db):
    '''
## jupyter

    > ch2 jupyter show ...

Show the template in the browser, starting a background Jupyter server if necessary.

    > ch2 jupyter list

List the available templates and their arguments.

    > ch2 jupyter status

Indicate whether the background server is running or not.

    > ch2 jupyter stop

Stop the background server.
    '''
    cmd = args[SUB_COMMAND]
    if cmd == LIST:
        print_list()
    else:
        c = JupyterController(args, system)
        if cmd == STATUS:
            status(c, system)  # todo - move to controller?
        elif cmd == SHOW:
            set_controller(c)  # c is passed implicitly to template via global
            show(args)
        elif cmd == SERVICE:
            c.run_local()
        elif cmd == START:
            c.start_service(restart=True)
        elif cmd == STOP:
            c.stop_service()
        else:
            raise Exception(f'Unexpected command {cmd}')


def status(c, system):
    if system.exists_any_process(JupyterServer):
        print('\n  Service running:')
        url = c.connection_url()
        print(f'    {url}')
        dir = c.notebook_dir()
        print(f'    {dir}\n')
    else:
        print('\n  No service running\n')


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


def print_list():
    for name, (_, spec) in templates():
        args = ' '.join(spec.args)
        if spec.varargs:
            if args: args += ' '
            args += '*' + spec.varargs
        print(f'\n  {name}  {args}')
    print()


def show(args):
    name = args[NAME]
    params = args[ARG]
    try:
        fn, spec = dict(templates())[name]
        params = check_params(params, spec)
        fn(*params)
    except KeyError:
        raise Exception(f'No template called {name} (see {PROGNAME} {JUPYTER} {LIST})')


def check_params(params, spec):
    if len(params) < len(spec.args) or (not spec.varargs and len(params) > len(spec.args)):
        raise Exception(f'Received {len(params)} args but need {"at least " if spec.varargs else ""}'
                        f'{len(spec.args)} values (see {PROGNAME} {JUPYTER} {LIST})')
    return params
