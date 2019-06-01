
from inspect import getfullargspec
from logging import getLogger
from pkgutil import iter_modules

from .args import SUB_COMMAND, SERVICE, START, STOP, SHOW, JUPYTER, LIST, PROGNAME, NAME, ARG, STATUS
from ..squeal import SystemProcess
from ..uranus import template
from ..uranus.server import JupyterServer, get_controller

log = getLogger(__name__)


def jupyter(args, db):
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
    if args[SUB_COMMAND] == SERVICE:
        service()
    elif args[SUB_COMMAND] == START:
        start()
    elif args[SUB_COMMAND] == STOP:
        stop()
    elif args[SUB_COMMAND] == SHOW:
        show(db, args)
    elif args[SUB_COMMAND] == STATUS:
        status(db)
    elif args[SUB_COMMAND] == LIST:
        print_list()
    else:
        raise Exception(f'Unexpected command {args[SUB_COMMAND]}')


def service():
    '''
    Start in this thread.
    '''
    get_controller().run_local()


def start():
    get_controller().start_service(restart=True)


def stop():
    get_controller().stop_service()


def status(db):
    with db.session_context() as s:
        if SystemProcess.exists_any(s, JupyterServer):
            print('\n  Service running:')
            url = get_controller().connection_url()
            print(f'    {url}')
            dir = get_controller().notebook_dir()
            print(f'    {dir}\n')
        else:
            print('\n  No service running\n')


def templates():
    log.debug(dir(template))
    log.debug(template.__file__)
    for importer, modname, ispkg in iter_modules(template.__path__):
        module = getattr(template, modname)
        function = getattr(module, modname)
        argspec = getfullargspec(function._original)
        yield modname, (function, argspec)


def print_list():
    for name, (_, spec) in templates():
        args = ' '.join(spec.args)
        print(f'\n  {name}  {args}')
    print()


def show(db, args):
    name = args[NAME]
    params = args[ARG]
    try:
        fn, spec = dict(templates())[name]
        params = build_params(params, spec)
        fn(*params)
    except KeyError:
        raise Exception(f'No template called {name} (see {PROGNAME} {JUPYTER} {LIST})')


def build_params(params, spec):
    if len(params) != len(spec.args):
        raise Exception(f'Received {len(params)} args but need {len(spec.args)} values ' +
                        f'(see {PROGNAME} {JUPYTER} {LIST})')
    return [build_param(param, name, spec.annotations.get(name, None)) for param, name in zip(params, spec.args)]


def build_param(param, name, annotation):
    if annotation:
        return annotation(param)
    else:
        return param

