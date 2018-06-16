
from .args import COMMAND, DIARY, INJURY, parser, NamespaceWithVariables
from .diary import main as diary
from .injury import main as injury


COMMANDS = {DIARY: diary,
            INJURY: injury}


def main():
    p = parser()
    ns = NamespaceWithVariables(p.parse_args())
    if COMMAND in ns:
        COMMANDS[ns[COMMAND]](ns)
    else:
        raise Exception('')
