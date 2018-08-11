
from .args import COMMAND, DIARY, INJURIES, parser, NamespaceWithVariables, SCHEDULES, PLAN, PACKAGE_FIT_PROFILE, \
    DUMP_FIT, PROGNAME, HELP, DEV
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
    log = make_log(args)
    try:
        if COMMAND in args:
            COMMANDS[args[COMMAND]](args, log)
        else:
            raise Exception('No command given')
    except Exception as e:
        log.critical(e)
        log.info('See "%s %s" for help' % (PROGNAME, HELP))
        if not args or args[DEV]:
            raise
