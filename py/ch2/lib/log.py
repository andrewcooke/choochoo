from contextlib import contextmanager
from logging import getLogger, DEBUG, Formatter, INFO, StreamHandler, WARNING
from logging.handlers import RotatingFileHandler
from sys import exc_info
from traceback import format_tb

from colorlog import ColoredFormatter

from ..commands.args import COMMAND, LOGS, PROGNAME, VERBOSITY, LOG, COLOR, DARK, LIGHT, DEV

log = getLogger(__name__)

STDERR_HANDLER = None
LOG_COLOR = 'log-color'


def make_log_from_args(args):

    name = args[LOG] if LOG in args and args[LOG] else (
            (args[COMMAND] if COMMAND in args and args[COMMAND] else PROGNAME) + f'.{LOG}')
    path = args.system_path(LOGS, name)
    verbosity = 5 if args[DEV] else args[VERBOSITY]

    make_log(path, verbosity=verbosity)


def make_log(path, verbosity=4):

    global STDERR_HANDLER

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

        if verbosity:
            stderr_formatter = Formatter('%(levelname)8s: %(message)s')
            STDERR_HANDLER = StreamHandler()
            STDERR_HANDLER.setLevel(level)
            STDERR_HANDLER.setFormatter(stderr_formatter)
            blog.addHandler(STDERR_HANDLER)
            tlog.addHandler(STDERR_HANDLER)
            wlog.addHandler(STDERR_HANDLER)
            clog.addHandler(STDERR_HANDLER)
            xlog.addHandler(STDERR_HANDLER)


def set_log_color(args, sys):
    color = args[COLOR]
    if color and color == color.upper():
        sys.set_constant(LOG_COLOR, color.lower(), force=True)
        color = None
    if color is None:
        color = sys.get_constant(LOG_COLOR, none=True)
    if STDERR_HANDLER and color:
        if color.lower() == LIGHT:
            STDERR_HANDLER.setFormatter(
                ColoredFormatter('%(log_color)s%(levelname)8s: %(message_log_color)s%(message)s',
                                 log_colors={'DEBUG': 'black',
                                             'INFO': 'black',
                                             'WARNING': 'black',
                                             'ERROR': 'black',
                                             'CRITICAL': 'black'},
                                 secondary_log_colors={'message':
                                                           {'DEBUG': 'yellow',
                                                            'INFO': 'black',
                                                            'WARNING': 'blue',
                                                            'ERROR': 'bold_red',
                                                            'CRITICAL': 'bold_red'}}))
        elif color.lower() == DARK:
            STDERR_HANDLER.setFormatter(
                ColoredFormatter('%(log_color)s%(levelname)8s: %(message_log_color)s%(message)s',
                                 log_colors={'DEBUG': 'white',
                                             'INFO': 'white',
                                             'WARNING': 'white',
                                             'ERROR': 'white',
                                             'CRITICAL': 'white'},
                                 secondary_log_colors={'message':
                                                           {'DEBUG': 'yellow',
                                                            'INFO': 'white',
                                                            'WARNING': 'cyan',
                                                            'ERROR': 'bold_red',
                                                            'CRITICAL': 'bold_red'}}))


def log_current_exception(traceback=True):
    t, e, tb = exc_info()
    try:
        log.debug(f'Exception: {e}')
    except:
        pass
    log.debug(f'Type: {t}')
    if traceback:
        log.warning('Traceback:\n' + ''.join(format_tb(tb)))


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