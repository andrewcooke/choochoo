from contextlib import contextmanager
from logging import getLogger, DEBUG, INFO, WARNING

from ..commands.args import base_system_path
from ..common.log import configure_log, log_current_exception
from ..common.names import UNDEF, COLOR, BASE

log = getLogger(__name__)


def make_log_from_args(args):
    from ..commands.args import LOG, COMMAND, VERBOSITY, PROGNAME, LOGS, DEV
    name = args[LOG] if LOG in args and args[LOG] else (
            (args[COMMAND] if COMMAND in args and args[COMMAND] else PROGNAME) + f'.{LOG}')
    path = base_system_path(args[BASE], subdir=LOGS, file=name)
    if args[VERBOSITY] is UNDEF:
        verbosity = 5 if args[DEV] else 2
    else:
        verbosity = args[VERBOSITY]
    configure_log('ch2', path, verbosity, {
        'sqlalchemy': WARNING,
        'matplotlib': INFO,
        'bokeh': DEBUG,
        'tornado': INFO,
        'sentinelsat': DEBUG,
        'werkzeug': DEBUG,
        'ch2': DEBUG,
        '__main__': DEBUG
    })


def update_log_color(args, data):
    from ..sql import SystemConstant
    color = args[COLOR]
    if color and color == color.upper():
        data.set_constant(SystemConstant.LOG_COLOR, color.lower(), force=True)
        color = None
    if color is None:
        color = data.get_constant(SystemConstant.LOG_COLOR, none=True)
    args[COLOR] = color


class Record:

    def __init__(self, log):
        self._log = log
        self._warning = []
        self._info = []

    def warning(self, msg):
        self._log.warning(msg)
        self._warning.append(msg)

    def info(self, msg):
        self._log.info(msg)
        self._info.append(msg)

    def raise_(self, msg):
        self.warning(msg)
        raise Exception(msg)

    @contextmanager
    def record_exceptions(self, catch=False):
        try:
            yield
        except Exception as e:
            self.warning(e)
            if catch:
                log_current_exception()
            else:
                raise

    def json(self):
        return {'warning': self._warning,
                'info': self._info}
