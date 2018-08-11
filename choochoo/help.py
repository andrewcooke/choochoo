
from .args import TOPIC


def help(args, logs, COMMANDS):
    if args[TOPIC] in COMMANDS:
        print(COMMANDS[args[TOPIC]].__doc__)
