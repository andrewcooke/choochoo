
from logging import getLogger, DEBUG, Formatter, INFO, StreamHandler, WARNING
from logging.handlers import RotatingFileHandler
from os.path import join
from sys import exc_info
from traceback import format_tb

from ..commands.args import COMMAND, LOGS, PROGNAME, VERBOSITY, LOG

log = getLogger(__name__)


def make_log(args, tui=False):

    if not getLogger('ch2').handlers:

        level_unset = args[VERBOSITY] is None
        level = 4 if level_unset else args[VERBOSITY][0]
        level = 10 * (6 - level)

        file_formatter = Formatter('%(levelname)-8s %(asctime)s: %(message)s')
        name = args[LOG] if LOG in args and args[LOG] else (
                (args[COMMAND] if COMMAND in args and args[COMMAND] else PROGNAME) + f'.{LOG}')
        path = join(args.dir(LOGS), name)
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

        clog = getLogger('ch2')
        clog.setLevel(DEBUG)
        clog.addHandler(file_handler)

        if not tui:
            stderr_formatter = Formatter('%(levelname)8s: %(message)s')
            stderr_handler = StreamHandler()
            stderr_handler.setLevel(level)
            stderr_handler.setFormatter(stderr_formatter)
            # slog.addHandler(stderr_handler)
            # mlog.addHandler(stderr_handler)
            blog.addHandler(stderr_handler)
            tlog.addHandler(stderr_handler)
            clog.addHandler(stderr_handler)


def log_current_exception():
    t, e, tb = exc_info()
    try:
        log.debug(f'Exception: {e}')
    except:
        pass
    log.debug(f'Type: {t}')
    log.debug('Traceback:\n' + ''.join(format_tb(tb)))
