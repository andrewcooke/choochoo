
from .command.activities import activities
from .command.args import COMMAND, parser, NamespaceWithVariables, PROGNAME, HELP, DEV, DIARY, FIT, \
    PACKAGE_FIT_PROFILE, ACTIVITIES, NO_OP, BASIC_CONFIG, CONSTANTS, STATISTICS, TEST_SCHEDULE, MONITOR, GARMIN
from .command.constants import constants
from .command.diary import diary
from .command.basic_config import basic_config
from .command.fit import fit
from .command.garmin import garmin
from .command.help import help
from .command.monitor import monitor
from .command.package_fit_profile import package_fit_profile
from .command.statistics import statistics
from .command.test_schedule import test_schedule
from .lib.log import make_log
from .squeal.database import Database


def no_op(args, log, db):
    '''
# no-op

This is used internally when accessing data in Jupyter or configuring the system
at the command line.
    '''
    pass


COMMANDS = {ACTIVITIES: activities,
            BASIC_CONFIG: basic_config,
            CONSTANTS: constants,
            DIARY: diary,
            FIT: fit,
            GARMIN: garmin,
            HELP: help,
            MONITOR: monitor,
            STATISTICS: statistics,
            NO_OP: no_op,
            PACKAGE_FIT_PROFILE: package_fit_profile,
            TEST_SCHEDULE: test_schedule,
            }


def main():
    p = parser()
    args = NamespaceWithVariables(p.parse_args())
    command_name = args[COMMAND] if COMMAND in args else None
    command = COMMANDS[command_name] if command_name in COMMANDS else None
    tui = command and hasattr(command, 'tui') and command.tui
    log = make_log(args, tui=tui)
    db = Database(args, log)
    try:
        if command:
            command(args, log, db)
        else:
            log.debug('If you are seeing the "No command given" error during development ' +
                      'you may have forgotten to set the command name via `set_defaults()`.')
            raise Exception('No command given (try `ch2 help`)')
    except KeyboardInterrupt:
        log.critical('User abort')
        pass
    except Exception as e:
        log.critical(e)
        log.info('See `%s %s` for available commands.' % (PROGNAME, HELP))
        log.info('Docs at http://andrewcooke.github.io/choochoo/index')
        if not args or args[DEV]:
            raise
