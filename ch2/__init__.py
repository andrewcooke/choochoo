
from glob import glob
from logging import getLogger, NullHandler
from os.path import abspath, dirname, join
from sys import version_info

getLogger('bokeh').addHandler(NullHandler())
getLogger('tornado').addHandler(NullHandler())


class FatalException(Exception):

    '''
    Base class for exceptions that we can't ignore at some higher level
    (fundamental things like bad config).
    '''

    pass


from .commands.activities import activities
from .commands.args import COMMAND, make_parser, NamespaceWithVariables, PROGNAME, HELP, DEV, DIARY, FIT, \
    PACKAGE_FIT_PROFILE, ACTIVITIES, NO_OP, CONFIG, CONSTANTS, STATISTICS, TEST_SCHEDULE, MONITOR, GARMIN, \
    UNLOCK, DUMP, FIX_FIT, CH2_VERSION, JUPYTER, KIT, WEB
from .commands.constants import constants
from .commands.dump import dump
from .commands.config import config
from .commands.diary import diary
from .commands.fit import fit
from .commands.fix_fit import fix_fit
from .commands.garmin import garmin
from .commands.help import help, LengthFmt
from .commands.jupyter import jupyter
from .commands.kit import kit
from .commands.monitor import monitor
from .commands.package_fit_profile import package_fit_profile
from .commands.statistics import statistics
from .commands.test_schedule import test_schedule
from .commands.unlock import unlock
from .commands.web import web
from .lib.io import tui
from .lib.log import make_log, log_current_exception
from .sql.database import Database
from .sql.system import System

log = getLogger(__name__)


@tui
def no_op(args, system, db):
    '''
## no-op

This is used internally when accessing data in Jupyter or configuring the system
at the command line.
    '''
    pass


COMMANDS = {ACTIVITIES: activities,
            CONSTANTS: constants,
            CONFIG: config,
            DIARY: diary,
            DUMP: dump,
            FIT: fit,
            FIX_FIT: fix_fit,
            GARMIN: garmin,
            HELP: help,
            JUPYTER: jupyter,
            KIT: kit,
            MONITOR: monitor,
            STATISTICS: statistics,
            NO_OP: no_op,
            PACKAGE_FIT_PROFILE: package_fit_profile,
            TEST_SCHEDULE: test_schedule,
            UNLOCK: unlock,
            WEB: web
            }


def main():
    parser = make_parser()
    ns = parser.parse_args()
    command_name = ns.command if hasattr(ns, COMMAND) else None
    command = COMMANDS[command_name] if command_name in COMMANDS else None
    if command and hasattr(command, 'tui') and command.tui:
        ns.tui = True
    args = NamespaceWithVariables(ns)
    make_log(args)
    log.info('Version %s' % CH2_VERSION)
    if version_info < (3, 7):
        raise Exception('Please user Python 3.7 or more recent')
    db = Database(args)
    system = System(args)
    try:
        if db.no_data() and (not command or command_name not in (CONFIG, PACKAGE_FIT_PROFILE, HELP)):
            refuse_until_configured(db.path)
        elif command:
            command(args, system, db)
        else:
            log.debug('If you are seeing the "No command given" error during development ' +
                      'you may have forgotten to set the command name via `set_defaults()`.')
            raise Exception('No command given (try `ch2 help`)')
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


def refuse_until_configured(path):
    dir = dirname(abspath(path))
    if len(glob(join(dir, '*'))) > 1:
        LengthFmt().print_all('''
Welcome to Choochoo.

There is no database available for this release, but you may have a database from a previous version.
For information on how to upgrade an old database, 
please see the documentation at http://andrewcooke.github.io/choochoo/version-upgrades

Otherwise, you will need to configure the system.
Please see the documentation at http://andrewcooke.github.io/choochoo''')
    else:
        LengthFmt().print_all('''
Welcome to Choochoo.

Before using the ch2 command you must configure the system.

Please see the documentation at http://andrewcooke.github.io/choochoo

To generate a default configuration use the command

    %s %s

NOTE: The default configuration is only an example.  Please see the docs
for more details.''' % (PROGNAME, CONFIG))
