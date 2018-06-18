
from .args import COMMAND, DIARY, INJURIES, parser, NamespaceWithVariables, AIMS
from .diary import main as diary
from .injury import main as injuries
from .aim import main as aims


COMMANDS = {DIARY: diary,
            INJURIES: injuries,
            AIMS: aims}


def main():
    p = parser()
    ns = NamespaceWithVariables(p.parse_args())
    if COMMAND in ns:
        COMMANDS[ns[COMMAND]](ns)
    else:
        raise Exception('')
