
from inspect import getfullargspec
from logging import getLogger
from pkgutil import iter_modules
from signal import pause
from time import sleep

from .args import SUB_COMMAND, SERVICE, START, STOP, SHOW, JUPYTER, LIST, PROGNAME, NAME, ARG, STATUS
from ..lib.workers import command_root
from ..squeal import SystemProcess
from ..uranus import template
from ..uranus.server import JupyterServer, start_service, STARTUP_SLEEP, start_remote

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
        service(db)
    elif args[SUB_COMMAND] == START:
        start(db)
    elif args[SUB_COMMAND] == STOP:
        stop(db)
    elif args[SUB_COMMAND] == SHOW:
        show(db, args)
    elif args[SUB_COMMAND] == STATUS:
        status(db)
    elif args[SUB_COMMAND] == LIST:
        print_list()
    else:
        raise Exception(f'Unexpected command {args[SUB_COMMAND]}')


def service(db):
    with db.session_context() as s:
        start_service(s)
        pause()


def start(db):
    with db.session_context() as s:

        def callback():
            ch2 = command_root()
            log_name = 'jupyter-service.log'
            cmd = f'{ch2} -v0 -l {log_name} {JUPYTER} {SERVICE}'
            SystemProcess.run(s, cmd, log_name, JupyterServer)
            sleep(STARTUP_SLEEP)

        start_remote(s, callback)


def stop(db):
    with db.session_context() as s:
        SystemProcess.delete_all(s, JupyterServer)


def status(db):
    with db.session_context() as s:
        if SystemProcess.exists_any(s, JupyterServer):
            print('\n  Service running\n')
        else:
            print('\n  No service running\n')


def templates():
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
    start(db)
    name = args[NAME]
    params = args[ARG]
    try:
        fn, spec = dict(templates())[name]
        params = build_params(params, spec)
        fn(*params, local=False)
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

