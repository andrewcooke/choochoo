
from .args import COMMAND, DIARY, INJURIES, parser, NamespaceWithVariables, SCHEDULES, PLAN, PACKAGE_FIT_PROFILE
from .diary import main as diary
from .fit.profile import package_fit_profile
from .injuries import main as injuries
from .plan import main as plan
from .schedules import main as schedules

COMMANDS = {DIARY: diary,
            INJURIES: injuries,
            SCHEDULES: schedules,
            PLAN: plan,
            PACKAGE_FIT_PROFILE: package_fit_profile}


def main():
    p = parser()
    ns = NamespaceWithVariables(p.parse_args())
    if COMMAND in ns:
        COMMANDS[ns[COMMAND]](ns)
    else:
        raise Exception('No command given')
