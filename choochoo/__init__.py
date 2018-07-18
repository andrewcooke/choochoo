
from .args import COMMAND, DIARY, INJURIES, parser, NamespaceWithVariables, SCHEDULES
from .diary import main as diary
from .injuries import main as injuries
from .schedules import main as schedules


COMMANDS = {DIARY: diary,
            INJURIES: injuries,
            SCHEDULES: schedules}


def main():
    p = parser()
    ns = NamespaceWithVariables(p.parse_args())
    if COMMAND in ns:
        COMMANDS[ns[COMMAND]](ns)
    else:
        raise Exception()
