from contextlib import contextmanager
from logging import getLogger, DEBUG, INFO, WARNING
from os.path import join

from ..commands.args import LOG_DIR
from ..common.log import configure_log, log_current_exception, set_log_color
from ..common.names import UNDEF, COLOR

log = getLogger(__name__)


def make_log_from_args(args):
    from ..commands.args import LOG, COMMAND, VERBOSITY, PROGNAME, DEV
    name = args[LOG] if LOG in args and args[LOG] else (
            (args[COMMAND] if COMMAND in args and args[COMMAND] else PROGNAME) + f'.{LOG}')
    path = join(args._format_path(LOG_DIR), name)
    if args[VERBOSITY] is UNDEF:
        verbosity = 5 if args[DEV] else 4
    else:
        verbosity = args[VERBOSITY]
    configure_log('ch2', path, verbosity, {
        'bokeh': DEBUG,
        'ch2': DEBUG,
        'jupyter': DEBUG,
        'matplotlib': DEBUG,
        'sentinelsat': DEBUG,
        'sqlalchemy': WARNING,
        'tornado': DEBUG,
        'werkzeug': DEBUG,
        '__main__': DEBUG
    })
    set_log_color(args[COLOR])
    log.info(f'Logging to {path}')


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
