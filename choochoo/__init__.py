
from .args import COMMAND, parser, NamespaceWithVariables, PROGNAME, HELP, DEV, DIARY, DUMP_FIT, INJURIES, \
    PLAN, PACKAGE_FIT_PROFILE, SCHEDULES
from .diary import diary
from .fit.profile.profile import package_fit_profile
from .fit.summary import dump_fit
from .help import help
from .injuries import injuries
from .log import make_log
from .plan import plan
from .schedules import schedules

COMMANDS = {DIARY: diary,
            DUMP_FIT: dump_fit,
            HELP: help,
            INJURIES: injuries,
            PLAN: plan,
            PACKAGE_FIT_PROFILE: package_fit_profile,
            SCHEDULES: schedules,
            }


def main():
    p = parser()
    args = NamespaceWithVariables(p.parse_args())
    command_name = args[COMMAND] if COMMAND in args else None
    command = COMMANDS[command_name] if command_name in COMMANDS else None
    tui = command and hasattr(command, 'tui') and command.tui
    log = make_log(args, tui=tui)
    try:
        if command_name == HELP:
            # avoid dependency loop
            help(args, log, COMMANDS)
        elif command:
            command(args, log)
        else:
            raise Exception('No command given (try `ch2 help`)')
    except Exception as e:
        log.critical(e)
        log.info('See "%s %s" for help' % (PROGNAME, HELP))
        if not args or args[DEV]:
            raise
