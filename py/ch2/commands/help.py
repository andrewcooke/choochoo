
from abc import abstractmethod, ABC
from logging import getLogger
from sys import stdout
import re

from .args import TOPIC, HELP, PROGNAME, BASE
from ..common.args import m
from ..lib.io import terminal_width

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


def help(args, data):
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
        Markdown().print(COMMANDS[args[TOPIC]].__doc__)
    else:
        Markdown().print(commands(COMMANDS))


BR = 'BR'
H = 'H'
P = 'P'
LI = 'LI'
PRE = 'PRE'


def parse(text):
    '''
    A very simple parser for the tiny subset of markdown that is used in comments.
    '''
    paragraph = ''
    for line in text.split('\n'):
        if line.strip().startswith('*'):
            if paragraph:
                yield P, paragraph
                paragraph = ''
            yield LI, line.strip().split(' ', 1)[1]
        elif line.strip() and line.startswith('  '):
            if paragraph:
                yield P, paragraph
                paragraph = ''
            yield PRE, line.strip()
        elif line.startswith('#'):
            if paragraph:
                yield P, paragraph
                paragraph = ''
            h, line = line.split(' ', 1)
            yield H + str(len(h)), line.strip()
        elif not line.strip():
            if paragraph:
                yield P, paragraph
                paragraph = ''
            yield BR, None
        elif paragraph:
            paragraph += ' ' + line.strip()
        else:
            paragraph = line
    if paragraph:
        yield P, paragraph


def filter(parser, yes=None, no=None):

    def filtered(text):
        for tag, value in parser(text):
            if yes and tag in yes:
                yield tag, value
            elif no and tag not in no:
                yield tag, value
            else:
                pass

    return filtered


class Formatter(ABC):

    def __init__(self, parser=None):
        self._parser = parser if parser else parse

    @abstractmethod
    def p(self, text):
        raise NotImplementedError

    @abstractmethod
    def li(self, text):
        raise NotImplementedError

    @abstractmethod
    def pre(self, text):
        raise NotImplementedError

    @abstractmethod
    def h(self, level, text):
        raise NotImplementedError

    @abstractmethod
    def br(self):
        raise NotImplementedError

    def format(self, text):
        for tag, text in self._parser(text):
            if tag == P: yield from self.p(text)
            elif tag == LI: yield from self.li(text)
            elif tag == PRE: yield from self.pre(text)
            elif tag == BR: yield from self.br()
            else: yield from self.h(int(tag[1:]), text)

    def str(self, text):
        return '\n'.join(self.format(text))

    def print(self, text, out=stdout):
        print(self.str(text), file=out)


class Markdown(Formatter):

    def __init__(self, width=None, margin=1, delta=0, parser=None):
        super().__init__(parser=parser)
        self._width = terminal_width(width) - margin
        self._margin = margin
        self._delta = delta

    def _chunks(self, text, first, rest=None):
        if rest is None: rest = first
        line = first
        for word in re.sub(r' +', ' ', text).split(' '):
            if line not in (first, rest):
                line += ' '
            if len(line + word) > self._width:
                yield line
                line = rest + word
            else:
                line += word
        if line: yield line

    def p(self, text):
        yield from self._chunks(text, ' ' * self._margin)

    def li(self, text):
        yield from self._chunks(text, (' ' * self._margin) + '* ', (' ' * self._margin) + '  ')

    def pre(self, text):
        yield (' ' * self._margin) + '    ' + text

    def h(self, level, text):
        yield (' ' * self._margin) + '#' * max(1, level + self._delta) + ' ' + text

    def br(self):
        yield ''


class HTML(Formatter):

    def __init__(self, delta=0, parser=None):
        super().__init__(parser=parser)
        self._delta = delta
        self._list = False

    def _ul(self, list):
        if self._list != list:
            if list: yield '<ul>'
            else: yield '</ul>'
            self._list = list

    def _tag(self, tag, text):
        yield f'<{tag}>'
        yield text
        yield f'</{tag}>'

    def p(self, text):
        yield from self._ul(False)
        yield from self._tag('p', text)

    def li(self, text):
        yield from self._ul(True)
        yield from self._tag('li', text)

    def pre(self, text):
        yield from self._ul(False)
        yield from self._tag('pre', text)

    def h(self, level, text):
        yield from self._ul(False)
        yield from self._tag('h' + str(max(1, level + self._delta)), text)

    def br(self):
        return
        yield
