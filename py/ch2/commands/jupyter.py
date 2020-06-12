from logging import getLogger

from .args import SUB_COMMAND, SERVICE, START, STOP, SHOW, JUPYTER, LIST, PROGNAME, NAME, ARG, STATUS
from ..jupyter.server import set_controller, JupyterController
from ..jupyter.utils import templates, get_template

log = getLogger(__name__)


def jupyter(args, data):
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
        list()
    else:
        c = JupyterController(data)
        if cmd == STATUS:
            c.status()
        elif cmd == SHOW:
            set_controller(c)  # c is passed implicitly to template via global
            show(args)
        elif cmd == SERVICE:
            c.service()
        elif cmd == START:
            c.start(restart=True)
        elif cmd == STOP:
            c.stop()
        else:
            raise Exception(f'Unexpected command {cmd}')


def list():
    for name, (_, spec) in templates().items():
        args = ' '.join(spec.args)
        if spec.varargs:
            if args: args += ' '
            args += '*' + spec.varargs
        print(f'\n  {name}  {args}')
    print()


def check_params(params, spec):
    if len(params) < len(spec.args) or (not spec.varargs and len(params) > len(spec.args)):
        raise Exception(f'Received {len(params)} args but need {"at least " if spec.varargs else ""}'
                        f'{len(spec.args)} values (see {PROGNAME} {JUPYTER} {LIST})')
    return params


def show(args):
    name = args[NAME]
    params = args[ARG]
    try:
        fn, spec = get_template(name)
        params = check_params(params, spec)
        fn(*params)
    except KeyError:
        raise Exception(f'No template called {name} (see {PROGNAME} {JUPYTER} {LIST})')
