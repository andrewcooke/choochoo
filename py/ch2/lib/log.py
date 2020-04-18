from contextlib import contextmanager
from logging import getLogger, DEBUG, Formatter, INFO, StreamHandler, WARNING
from logging.handlers import RotatingFileHandler
from sys import exc_info
from traceback import format_tb

from colorlog import ColoredFormatter

from ..commands.args import COMMAND, LOGS, PROGNAME, VERBOSITY, LOG, TUI


log = getLogger(__name__)


def make_log_from_args(args):

    name = args[LOG] if LOG in args and args[LOG] else (
            (args[COMMAND] if COMMAND in args and args[COMMAND] else PROGNAME) + f'.{LOG}')
    path = args.system_path(LOGS, name)

    make_log(path, verbosity=args[VERBOSITY], tui=args[TUI])


def make_log(path, verbosity=4, tui=False):

    if not getLogger('ch2').handlers:

        level = 10 * (6 - verbosity)

        file_formatter = Formatter('%(levelname)-8s %(asctime)s: %(message)s')
        file_handler = RotatingFileHandler(path, maxBytes=1e6, backupCount=10)
        file_handler.setLevel(DEBUG)
        file_handler.setFormatter(file_formatter)

        slog = getLogger('sqlalchemy')
        slog.setLevel(WARNING)
        slog.addHandler(file_handler)

        mlog = getLogger('matplotlib')
        mlog.setLevel(INFO)
        mlog.addHandler(file_handler)

        blog = getLogger('bokeh')
        blog.setLevel(DEBUG)
        blog.addHandler(file_handler)

        tlog = getLogger('tornado')
        tlog.setLevel(INFO)
        tlog.addHandler(file_handler)

        sslog = getLogger('sentinelsat')
        sslog.setLevel(DEBUG)
        sslog.addHandler(file_handler)

        wlog = getLogger('werkzeug')
        wlog.setLevel(DEBUG)
        wlog.addHandler(file_handler)

        clog = getLogger('ch2')
        clog.setLevel(DEBUG)
        clog.addHandler(file_handler)

        # capture logging from an executing module, if one exists
        xlog = getLogger('__main__')
        xlog.setLevel(DEBUG)
        xlog.addHandler(file_handler)

        if not tui:
            stderr_formatter = ColoredFormatter('%(levelname)8s: %(message_log_color)s%(message)s',
                                                secondary_log_colors={'message':
                                                    {'WARNING': 'yellow',
                                                     'ERROR': 'red',
                                                     'CRITICAL': 'red'}})
            stderr_handler = StreamHandler()
            stderr_handler.setLevel(level)
            stderr_handler.setFormatter(stderr_formatter)
            blog.addHandler(stderr_handler)
            tlog.addHandler(stderr_handler)
            wlog.addHandler(stderr_handler)
            clog.addHandler(stderr_handler)
            xlog.addHandler(stderr_handler)


def log_current_exception(traceback=True):
    t, e, tb = exc_info()
    try:
        log.debug(f'Exception: {e}')
    except:
        pass
    log.debug(f'Type: {t}')
    if traceback:
        log.debug('Traceback:\n' + ''.join(format_tb(tb)))


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
    def record_exceptions(self):
        try:
            yield
        except Exception as e:
            self.warning(e)
            raise

    def json(self):
        return {'warning': self._warning,
                'info': self._info}