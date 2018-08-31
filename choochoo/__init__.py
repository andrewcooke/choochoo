
from .activities import edit_activities
from .args import COMMAND, parser, NamespaceWithVariables, PROGNAME, HELP, DEV, DIARY, DUMP_FIT, EDIT_INJURIES, \
    ADD_PLAN, PACKAGE_FIT_PROFILE, EDIT_SCHEDULES, EDIT_ACTIVITIES
from .diary import diary
from .fit.profile.profile import package_fit_profile
from .fit.summary import dump_fit
from .help import help
from .injuries import edit_injuries
from .log import make_log
from .plan import add_plan
from .schedules import edit_schedules

COMMANDS = {ADD_PLAN: add_plan,
            EDIT_ACTIVITIES: edit_activities,
            EDIT_INJURIES: edit_injuries,
            EDIT_SCHEDULES: edit_schedules,
            DIARY: diary,
            DUMP_FIT: dump_fit,
            HELP: help,
            PACKAGE_FIT_PROFILE: package_fit_profile,
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
        log.info('See `%s %s` for help' % (PROGNAME, HELP))
        if not args or args[DEV]:
            raise
