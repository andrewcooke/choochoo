
from logging import getLogger, DEBUG, Formatter, INFO, StreamHandler, NullHandler
from logging.handlers import RotatingFileHandler
from os.path import join

from ..command.args import COMMAND, LOGS, PROGNAME, VERBOSITY


CACHE = []


def make_log(args, tui=False):

    if not CACHE:

        level_unset = args[VERBOSITY] is None
        level = 4 if level_unset else args[VERBOSITY][0]
        level = 10 * (6 - level)

        file_formatter = Formatter('%(levelname)-8s %(asctime)s: %(message)s')
        name = args[COMMAND] if COMMAND in args else PROGNAME
        path = join(args.dir(LOGS), name + '.log')
        file_handler = RotatingFileHandler(path, maxBytes=1e6, backupCount=10)
        file_handler.setLevel(DEBUG)
        file_handler.setFormatter(file_formatter)

        slog = getLogger('sqlalchemy')
        slog.setLevel(INFO)
        slog.addHandler(file_handler)

        mlog = getLogger('matplotlib')
        mlog.setLevel(INFO)
        mlog.addHandler(file_handler)

        blog = getLogger('bokeh')
        blog.setLevel(INFO)
        blog.addHandler(file_handler)

        tlog = getLogger('tornado')
        tlog.setLevel(INFO)
        tlog.addHandler(file_handler)

        log = getLogger(name)
        log.setLevel(DEBUG)
        log.addHandler(file_handler)

        if not tui or not level_unset:
            stderr_formatter = Formatter('%(levelname)8s: %(message)s')
            stderr_handler = StreamHandler()
            stderr_handler.setLevel(level)
            stderr_handler.setFormatter(stderr_formatter)
            log.addHandler(stderr_handler)
            # slog.addHandler(stderr_handler)
            # mlog.addHandler(stderr_handler)
            # blog.addHandler(stderr_handler)
            # tlog.addHandler(stderr_handler)

        CACHE.append(log)

    return CACHE[0]
