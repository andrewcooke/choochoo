
from glob import glob
from logging import getLogger, NullHandler
from os.path import abspath, dirname, join
from sqlite3 import enable_callback_tracebacks
from sys import version_info

getLogger('bokeh').addHandler(NullHandler())
getLogger('tornado').addHandler(NullHandler())


class FatalException(Exception):

    '''
    Base class for exceptions that we can't ignore at some higher level
    (fundamental things like bad config).
    '''

    pass


from .commands.args import COMMAND, make_parser, NamespaceWithVariables, PROGNAME, HELP, DEV, DIARY, FIT, \
    PACKAGE_FIT_PROFILE, ACTIVITIES, NO_OP, DATABASE, CONSTANTS, CALCULATE, SHOW_SCHEDULE, MONITOR, GARMIN, \
    UNLOCK, DUMP, FIX_FIT, CH2_VERSION, JUPYTER, KIT, WEB, READ, IMPORT, THUMBNAIL, CHECK, SEARCH, VALIDATE, BASE
from .commands.constants import constants
from .commands.validate import validate
from .commands.database import database
from .commands.fit import fit
from .commands.fix_fit import fix_fit
from .commands.garmin import garmin
from .commands.help import help, Markdown
from .commands.import_ import import_
from .commands.jupyter import jupyter
from .commands.kit import kit
from .commands.package_fit_profile import package_fit_profile
from .commands.search import search
from .commands.calculate import calculate
from .commands.show_schedule import show_schedule
from .commands.thumbnail import thumbnail
from .commands.unlock import unlock
from .commands.read import read
from .commands.web import web
from .lib.io import tui
from .lib.log import make_log_from_args, set_log_color
from .sql.database import SystemConstant
from .sql.system import System

log = getLogger(__name__)


@tui  # todo - can we drop this and remove tui completely?
def no_op(args, system, db):
    '''
## no-op

This is used internally when accessing data in Jupyter or configuring the system
at the command line.
    '''
    pass


COMMANDS = {CONSTANTS: constants,
            DATABASE: database,
            FIT: fit,
            FIX_FIT: fix_fit,
            GARMIN: garmin,
            HELP: help,
            IMPORT: import_,
            JUPYTER: jupyter,
            KIT: kit,
            CALCULATE: calculate,
            NO_OP: no_op,
            PACKAGE_FIT_PROFILE: package_fit_profile,
            READ: read,
            SEARCH: search,
            SHOW_SCHEDULE: show_schedule,
            THUMBNAIL: thumbnail,
            UNLOCK: unlock,
            VALIDATE: validate,
            WEB: web
            }


def main():
    from . import commands
    parser = make_parser()
    ns = parser.parse_args()
    command_name = ns.command if hasattr(ns, COMMAND) else None
    command = COMMANDS[command_name] if command_name in COMMANDS else None
    if command and hasattr(command, 'tui') and command.tui:
        ns.verbose = 0
    args = NamespaceWithVariables(ns)
    commands.args.GLOBAL_DEV_FLAG = args[DEV]
    log.debug(f'Global dev flag: {commands.args.GLOBAL_DEV_FLAG}')
    make_log_from_args(args)
    log.info('Version %s' % CH2_VERSION)
    if version_info < (3, 7):
        raise Exception('Please user Python 3.7 or more recent')
    sys = System(args[BASE])
    db = sys.get_database()
    enable_callback_tracebacks(True)  # experimental - wondering what this does / whether it is useful?
    set_log_color(args, sys)
    try:
        if not command:
            log.debug('If you are seeing the "No command given" error during development ' +
                      'you may have forgotten to set the command name via `set_defaults()`.')
            raise Exception('No command given (try `ch2 help`)')
        elif not db:
            if command_name not in (DATABASE, PACKAGE_FIT_PROFILE, HELP):
                refuse_until_configured(False)
        elif db.no_data():
            if command_name not in (DATABASE, PACKAGE_FIT_PROFILE, HELP, WEB):
                refuse_until_configured(True)
        command(args, sys, db)
    except KeyboardInterrupt:
        log.critical('User abort')
        exit(1)
    except Exception as e:
        log.critical(e)
        log.info('See `%s %s` for available commands.' % (PROGNAME, HELP))
        log.info('Docs at http://andrewcooke.github.io/choochoo')
        if not args or args[DEV]:
            raise
        exit(2)


def refuse_until_configured(exists):
        Markdown().print(f'''
Welcome to Choochoo.

You must configure the database before use.

Please use the {PROGNAME} {DATABASE} command.
''')