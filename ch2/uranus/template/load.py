
from abc import abstractmethod, ABC
from inspect import getsource
from re import compile
from sys import stdout

import nbformat as nb
import nbformat.v4 as nbv

QUOTES = "'''"


class Token(ABC):

    def __init__(self, vars):
        self._vars = vars

    # called when this token is complete
    def post_one(self):
        pass

    # called when all tokens are complete
    def post_all(self, tokens):
        pass

    @abstractmethod
    def to_cell(self):
        raise NotImplementedError()

    @staticmethod
    def to_notebook(tokens):
        for token in tokens:
            token.post_all(tokens)
        notebook = nbv.new_notebook()
        for token in tokens:
            notebook['cells'].append(token.to_cell())
        return notebook


class TextToken(Token):

    def __init__(self, vars, indent):
        super().__init__(vars)
        self._indent = indent
        self._text = ''

    def append(self, line):
        self._text += line[self._indent:]
        self._text += '\n'

    def __bool__(self):
        return bool(self._text)

    @staticmethod
    def _strip(text):
        while text.startswith('\n'):
            text = text[1:]
        while text.endswith('\n'):
            text = text[:-1]
        return text

    def __repr__(self):
        return "%s(%s\n%s\n%s)" % (self.__class__.__name__, QUOTES, self._text, QUOTES)

    def to_cell(self):
        return nbv.new_markdown_cell(self._text)


class Text(TextToken):

    def __init__(self, vars, f, indent):
        super().__init__(vars, indent)
        self._fmt = 'f' + QUOTES if f else QUOTES

    def post_one(self):
        self._text = eval('%s%s%s' % (self._fmt, self._text, QUOTES), self._vars)
        self._text = self._strip(self._text)

    def post_all(self, tokens):
        self._text = '\n'.join(self._expand_line(line, tokens) for line in self._text.splitlines())

    def _expand_line(self, line, tokens):
        if line == '$contents':
            return '## Contents\n' + self._contents(tokens)
        else:
            return line

    def _contents(self, tokens):
        sections = []
        for token in tokens:
            if isinstance(token, Text):
                for line in token._text.splitlines():
                    if line.startswith('## '):
                        title = line[3:].strip()
                        sections.append('* [%s](%s)' % (title, title.replace(' ', '-')))
        return '\n'.join(sections)

    @staticmethod
    def parse(vars, lines, f):
        text = Text(vars, f, 4)
        while lines and lines[0].strip() != QUOTES:
            text.append(lines.pop(0))
        if text:
            text.post_one()
            yield text
        if lines:
            yield from Params.parse_text_or_code(vars, lines[1:])


class Code(TextToken):

    def to_cell(self):
        return nbv.new_code_cell(self._strip(self._text))

    @staticmethod
    def parse(vars, lines):
        code = Code(vars, 4)
        while lines and lines[0].strip() != QUOTES:
            code.append(lines.pop(0))
        if code:
            code.post_one()
            yield code
        if lines:
            yield from Params.parse_text_or_code(vars, lines)


class Import(Code):

    @staticmethod
    def parse(vars, lines):
        imports = Import(vars, 0)
        while lines:
            if lines[0].startswith('def '):
                if imports:
                    imports.post_one()
                    yield imports
                yield from Params.parse(vars, lines)
                return
            else:
                imports.append(lines.pop(0))


class Params(Code):

    def __init__(self, vars, params):
        super().__init__(vars, 0)
        self._params = [param.strip() for param in params]

    def post_one(self):
        for param in self._params:
            self.append("%s = '%s'" % (param, self._vars[param]))

    @staticmethod
    def parse(vars, lines):
        line = lines.pop(0)
        template = compile(r'def template\(([^)]*)\):\s*')
        match = template.match(line)
        if match.group(1):
            params = Params(vars, match.group(1).split(','))
            params.post_one()
            yield params
        elif not match:
            raise Exception('Bad template def: %s' % line)
        yield from Params.parse_text_or_code(vars, lines)

    @staticmethod
    def parse_text_or_code(vars, lines):
        while lines and not lines[0].strip():
            lines.pop(0)
        if lines:
            if lines[0].strip() == QUOTES:
                yield from Text.parse(vars, lines[1:], False)
            elif lines[0].strip() == 'f' + QUOTES:
                yield from Text.parse(vars, lines[1:], True)
            else:
                yield from Code.parse(vars, lines)


def tokenize(vars, text):
    yield from Import.parse(vars, list(text.splitlines()))


def load(name):
    template = getattr(__import__('ch2.uranus.template', fromlist=[name]), name)
    return getsource(template)


if __name__ == '__main__':
    tokens = list(tokenize({'activity_date': '2018-03-01 16:00', 'compare_date': '2017-09-19 16:00'},
                           load('compare_activities')))
    print(tokens)
    notebook = Token.to_notebook(tokens)
    nb.write(notebook, stdout)