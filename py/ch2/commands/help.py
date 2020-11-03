from logging import getLogger

from .args import TOPIC, HELP, PROGNAME
from ..common.args import m
from ..common.md import Markdown

log = getLogger(__name__)


def commands(COMMANDS):
    from .args import H
    return '''
Thank-you for using Choochoo.  Please send feedback to andrew@acooke.org

# Commands

* %s

See also `%s %s` for usage, '%s %s CMD` for guidance on a particular command, 
and `%s %s CMD` for usage of that command.

Docs at http://andrewcooke.github.io/choochoo/index''' % (
        '\n* '.join(COMMANDS.keys()), PROGNAME, m(H), PROGNAME, HELP, PROGNAME, m(H))


def help(config):
    '''
## help

    > ch2 help [topic]

Displays help for a particular topic.

### Examples

    > ch2 help help

Displays this information.

    > ch2 help

Lists available topics.
    '''
    from .. import COMMANDS
    args = config.args
    if args[TOPIC] in COMMANDS:
        Markdown().print(COMMANDS[args[TOPIC]].__doc__)
    else:
        Markdown().print(commands(COMMANDS))


