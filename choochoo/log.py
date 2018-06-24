
from logging import getLogger, DEBUG, Formatter
from logging.handlers import RotatingFileHandler
from os.path import join

from .args import COMMAND, LOGS


def make_log(args):

    log = getLogger(args[COMMAND])
    log.setLevel(DEBUG)

    file_formatter = Formatter('%(levelname)-8s %(asctime)s: %(message)s')
    path = join(args.dir(LOGS), args[COMMAND] + '.log')
    file_handler = RotatingFileHandler(path, maxBytes=1e6, backupCount=10)
    file_handler.setLevel(DEBUG)
    file_handler.setFormatter(file_formatter)
    log.addHandler(file_handler)

    return log

