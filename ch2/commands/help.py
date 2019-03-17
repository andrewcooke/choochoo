
from abc import abstractmethod
from logging import getLogger
from sys import stdout

from .args import TOPIC, HELP, PROGNAME, m, H, DEFAULT_CONFIG
from ..lib.io import terminal_width

log = getLogger(__name__)


class Fmt:

    def print_all(self, text):
        self.print()
        for para in self.paras(text):
            self.print(para)
        self.print()

    def paras(self, text):
        para = ''
        for line in text.split('\n'):
            if line.strip().startswith('*'):
                if para:
                    yield para
                para = line
            elif para and not line:
                yield para
                yield ''
                para = ''
            elif para:
                para += ' ' + line
            else:
                para = line
        if para:
            yield para

    @abstractmethod
    def print(self, para=None):
        raise NotImplementedError()


class LengthFmt(Fmt):

    def __init__(self, stream=stdout, width=None, margin=1):
        self.__out = stream
        self.__width = terminal_width(width) - margin
        self.__margin = margin

    def print(self, text=None):
        if text:
            indent = ' ' * self.__margin
            while text and text[0] == ' ':
                indent += ' '
                text = text[1:]
            line = indent
            while text:
                try:
                    word, text = text.split(' ', 1)
                except ValueError:
                    word, text = text, ''
                if len(line) == len(indent):
                    line += word
                elif len(line) + 1 + len(word) <= self.__width:
                    line += ' ' + word
                else:
                    print(line, file=self.__out)
                    line = indent + word
            print(line, file=self.__out)
        else:
            print(file=self.__out)


def commands(COMMANDS):
    return '''
Thank-you for using Choochoo.  Please send feedback to andrew@acooke.org

# Commands

* %s

See also `%s %s` for usage, '%s %s CMD` for guidance on a particular command, 
and `%s %s CMD` for usage of that command.

Docs at http://andrewcooke.github.io/choochoo/index''' % (
        '\n* '.join(COMMANDS.keys()), PROGNAME, m(H), PROGNAME, HELP, PROGNAME, m(H))


def help(args, db):
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
    if args[TOPIC] in COMMANDS:
        LengthFmt().print_all(COMMANDS[args[TOPIC]].__doc__)
    else:
        LengthFmt().print_all(commands(COMMANDS))
