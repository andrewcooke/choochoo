from logging import getLogger, Formatter, DEBUG, StreamHandler
from logging.handlers import RotatingFileHandler
from sys import exc_info
from traceback import format_tb

from colorlog import ColoredFormatter

from .names import DARK, LIGHT, UNDEF

log = getLogger(__name__)
STDERR_HANDLER = None


def configure_log(name, path, verbosity, levels=None):

    global STDERR_HANDLER
    levels = levels or {}

    if not getLogger(name).handlers:
        file_formatter = Formatter('%(levelname)-8s %(asctime)s: %(message)s')
        file_handler = RotatingFileHandler(path, maxBytes=1e6, backupCount=10)
        file_handler.setLevel(DEBUG)
        file_handler.setFormatter(file_formatter)
        for root, level in levels.items():
            log = getLogger(root)
            log.setLevel(level)
            log.addHandler(file_handler)

        if verbosity:
            stderr_formatter = Formatter('%(levelname)8s: %(message)s')
            STDERR_HANDLER = StreamHandler()
            STDERR_HANDLER.setLevel(10 * (6 - verbosity))
            STDERR_HANDLER.setFormatter(stderr_formatter)
            for root in levels:
                log = getLogger(root)
                log.addHandler(STDERR_HANDLER)


def set_log_color(color):

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
                                                            'INFO': 'blue',
                                                            'WARNING': 'black',
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


def log_current_exception(traceback=UNDEF, exception_level=DEBUG, traceback_level=DEBUG):
    from .global_ import global_dev
    if traceback is UNDEF: traceback = global_dev()
    t, e, tb = exc_info()
    try:
        log.log(exception_level, f'Exception: {e}')
    except:
        pass
    log.log(exception_level, f'Type: {t}')
    if traceback:
        log.log(traceback_level, 'Traceback:\n' + ''.join(format_tb(tb)))


def first_line(exception):
    return str(exception).splitlines()[0]
