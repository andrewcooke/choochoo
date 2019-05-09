
from logging import getLogger, NullHandler
from sys import version_info

getLogger('bokeh').addHandler(NullHandler())
getLogger('tornado').addHandler(NullHandler())

from .commands.activities import activities
from .commands.args import COMMAND, parser, NamespaceWithVariables, PROGNAME, HELP, DEV, DIARY, FIT, \
    PACKAGE_FIT_PROFILE, ACTIVITIES, NO_OP, DEFAULT_CONFIG, CONSTANTS, STATISTICS, TEST_SCHEDULE, MONITOR, GARMIN, \
    UNLOCK, DUMP, FIX_FIT, CH2_VERSION, JUPYTER
from .commands.constants import constants
from .commands.dump import dump
from .commands.default_config import default_config
from .commands.diary import diary
from .commands.fit import fit
from .commands.fix_fit import fix_fit
from .commands.garmin import garmin
from .commands.jupyter import jupyter
from .commands.help import help, LengthFmt
from .commands.monitor import monitor
from .commands.package_fit_profile import package_fit_profile
from .commands.statistics import statistics
from .commands.test_schedule import test_schedule
from .commands.unlock import unlock
from .lib.io import tui
from .lib.log import make_log, log_current_exception
from .squeal.database import Database
from .squeal import SystemConstant
from .uranus.server import stop_local, set_server_args

log = getLogger(__name__)


@tui
def no_op(args, db):
    '''
## no-op

This is used internally when accessing data in Jupyter or configuring the system
at the command line.
    '''
    pass


COMMANDS = {ACTIVITIES: activities,
            CONSTANTS: constants,
            DEFAULT_CONFIG: default_config,
            DIARY: diary,
            DUMP: dump,
            FIT: fit,
            FIX_FIT: fix_fit,
            GARMIN: garmin,
            JUPYTER: jupyter,
            HELP: help,
            MONITOR: monitor,
            STATISTICS: statistics,
            NO_OP: no_op,
            PACKAGE_FIT_PROFILE: package_fit_profile,
            TEST_SCHEDULE: test_schedule,
            UNLOCK: unlock,
            }


def main():
    args = NamespaceWithVariables(parser().parse_args())
    command_name = args[COMMAND] if COMMAND in args else None
    command = COMMANDS[command_name] if command_name in COMMANDS else None
    tui = command and hasattr(command, 'tui') and command.tui
    make_log(args, tui=tui)
    log.info('Version %s' % CH2_VERSION)
    if version_info < (3, 7):
        raise Exception('Please user Python 3.7 or more recent')
    db = Database(args, log)
    try:
        if db.is_empty() and (not command or command_name != DEFAULT_CONFIG):
            refuse_until_configured()
        else:
            set_server_args(args)
            try:
                if command:
                    command(args, db)
                else:
                    log.debug('If you are seeing the "No command given" error during development ' +
                              'you may have forgotten to set the command name via `set_defaults()`.')
                    raise Exception('No command given (try `ch2 help`)')
            finally:
                stop_local()
    except KeyboardInterrupt:
        log.critical('User abort')
        exit(1)
    except Exception as e:
        log.critical(e)
        log_current_exception()
        log.info('See `%s %s` for available commands.' % (PROGNAME, HELP))
        log.info('Docs at http://andrewcooke.github.io/choochoo')
        if not args or args[DEV]:
            raise
        exit(2)


def refuse_until_configured():
    LengthFmt().print_all('''
Welcome to Choochoo.

Before using the ch2 command you must configure the system.

Please see the documentation at http://andrewcooke.github.io/choochoo

To generate a default configuration use the command

    %s %s

NOTE: The default configuration is only an example.  Please see the docs
for more details.''' % (PROGNAME, DEFAULT_CONFIG))
