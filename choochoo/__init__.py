
from .args import COMMAND, DIARY, parser, NamespaceWithVariables
from .diary import main as diary


COMMANDS = {DIARY: diary}


def main():
    p = parser()
    ns = NamespaceWithVariables(p.parse_args())
    if COMMAND in ns:
        COMMANDS[ns[COMMAND]](ns)
    else:
        raise Exception('')
