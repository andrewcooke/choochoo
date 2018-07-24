
from .args import COMMAND, DIARY, INJURIES, parser, NamespaceWithVariables, SCHEDULES, PLAN
from .diary import main as diary
from .injuries import main as injuries
from .plan import main as plan
from .schedules import main as schedules


COMMANDS = {DIARY: diary,
            INJURIES: injuries,
            SCHEDULES: schedules,
            PLAN: plan}


def main():
    p = parser()
    ns = NamespaceWithVariables(p.parse_args())
    if COMMAND in ns:
        COMMANDS[ns[COMMAND]](ns)
    else:
        raise Exception('No command given')
