
from .args import COMMAND, DIARY, INJURIES, parser, NamespaceWithVariables, AIMS, REMINDERS
from .diary import main as diary
from .injuries import main as injuries
from .aims import main as aims
from .reminders import main as reminders


COMMANDS = {DIARY: diary,
            INJURIES: injuries,
            AIMS: aims,
            REMINDERS: reminders}


def main():
    p = parser()
    ns = NamespaceWithVariables(p.parse_args())
    if COMMAND in ns:
        COMMANDS[ns[COMMAND]](ns)
    else:
        raise Exception()
