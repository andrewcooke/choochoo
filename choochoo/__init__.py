
from .args import COMMAND, DIARY, INJURIES, parser, NamespaceWithVariables, AIMS, REMINDERS
from .diary import main as diary
from .injuries import main as injuries


COMMANDS = {DIARY: diary,
            INJURIES: injuries}


def main():
    p = parser()
    ns = NamespaceWithVariables(p.parse_args())
    if COMMAND in ns:
        COMMANDS[ns[COMMAND]](ns)
    else:
        raise Exception()
