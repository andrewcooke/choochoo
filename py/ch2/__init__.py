from logging import getLogger, NullHandler
from sys import version_info, exit

from .common.args import NamespaceWithVariables
from .common.global_ import set_global_dev
from .common.md import Markdown
from .common.names import COLOR, BASE, DB

getLogger('bokeh').addHandler(NullHandler())
getLogger('tornado').addHandler(NullHandler())


class FatalException(Exception):

    '''
    Base class for exceptions that we can't ignore at some higher level
    (fundamental things like bad config).
    '''

    pass


from .commands.args import COMMAND, make_parser, PROGNAME, HELP, DEV, DIARY, FIT, \
    PACKAGE_FIT_PROFILE, ACTIVITIES, NO_OP, DATABASE, CONSTANTS, SHOW_SCHEDULE, MONITOR, GARMIN, \
    UNLOCK, DUMP, FIX_FIT, CH2_VERSION, JUPYTER, KIT, WEB, IMPORT, THUMBNAIL, CHECK, SEARCH, VALIDATE, \
    DB_VERSION, UPLOAD, PROCESS
from .commands.process import process
from .commands.upload import upload
from .commands.constants import constants
from .commands.validate import validate
from .commands.db import db
from .commands.fit import fit
from .commands.fix_fit import fix_fit
from .commands.help import help
from .commands.import_ import import_
from .commands.jupyter import jupyter
from .commands.kit import kit
from .commands.package_fit_profile import package_fit_profile
from .commands.search import search
from .commands.show_schedule import show_schedule
from .commands.thumbnail import thumbnail
from .commands.web import web
from .lib.log import make_log_from_args
from .sql.database import SystemConstant
from .lib.cprofile import profile
from .sql.config import Config

log = getLogger(__name__)


def no_op(args, system, db):
    '''
## no-op

This is used internally when accessing data in Jupyter or configuring the system
at the command line.
    '''
    pass


COMMANDS = {CONSTANTS: constants,
            DB: db,
            FIT: fit,
            FIX_FIT: fix_fit,
            HELP: help,
            IMPORT: import_,
            JUPYTER: jupyter,
            KIT: kit,
            NO_OP: no_op,
            PACKAGE_FIT_PROFILE: package_fit_profile,
            PROCESS: process,
            SEARCH: search,
            SHOW_SCHEDULE: show_schedule,
            THUMBNAIL: thumbnail,
            UPLOAD: upload,
            VALIDATE: validate,
            WEB: web
            }


def args_and_command():
    parser = make_parser()
    ns = parser.parse_args()
    command_name = ns.command if hasattr(ns, COMMAND) else None
    command = COMMANDS[command_name] if command_name in COMMANDS else None
    if command_name == NO_OP: ns.verbose = 0
    args = NamespaceWithVariables._from_ns(ns, PROGNAME, DB_VERSION)
    return args, command, command_name


def versions():
    log.info('Version %s' % CH2_VERSION)
    if version_info < (3, 7):
        raise Exception('Please user Python 3.7 or more recent')


def main():
    versions()
    args, command, command_name = args_and_command()
    set_global_dev(args[DEV])
    make_log_from_args(args)
    config = Config(args)
    with profile(args):
        try:
            if not command:
                log.debug('If you are seeing the "No command given" error during development ' +
                          'you may have forgotten to set the command name via `set_defaults()`.')
                raise Exception('No command given (try `ch2 help`)')
            elif command_name not in (DB, PACKAGE_FIT_PROFILE, HELP, IMPORT):
                db = None
                try:
                    db = config.db if command_name not in (PACKAGE_FIT_PROFILE, HELP) else None
                except Exception as e:
                    log.warning(e)
                if not db:
                    refuse_until_configured(command_name, False)
                elif db.no_data():
                    refuse_until_configured(command_name, True)
            command(config)
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


def refuse_until_configured(command_name, uri):
    Markdown().print(f'''
Welcome to Choochoo.

You must configure the database before use (no {"schema" if uri else "uri"}).

Please use the {PROGNAME} {DATABASE} command.
''')
    if command_name != WEB:
        exit(3)
