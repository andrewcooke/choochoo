
from inspect import getsource
from re import compile
from sys import stdout

import nbformat as nb
import nbformat.v4 as nbv

QUOTES = "'''"


class Token:

    def expand(self, tokens):
        pass

    @staticmethod
    def to_notebook(tokens):
        for token in tokens:
            token.expand(tokens)
        notebook = nbv.new_notebook()
        for token in tokens:
            notebook['cells'].append(token.to_cell())
        return notebook


class TextToken(Token):

    def __init__(self, indent):
        self._indent = indent
        self._text = ''

    def append(self, line):
        self._text += line[self._indent:]
        self._text += '\n'

    def __bool__(self):
        return bool(self._text)

    def strip(self):
        text = self._text
        while text.startswith('\n'):
            text = text[1:]
        while text.endswith('\n'):
            text = text[:-1]
        return text

    def __repr__(self):
        return "%s(%s\n%s\n%s)" % (self.__class__.__name__, QUOTES, self.strip(), QUOTES)

    def to_cell(self):
        return nbv.new_markdown_cell(self.strip())


class Params(Token):

    def __init__(self, params):
        self._params = [param.strip() for param in params]

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, ', '.join(self._params))

    def to_cell(self):
        return nbv.new_raw_cell()

    @staticmethod
    def parse(lines):
        line = lines.pop(0)
        template = compile(r'def template\(([^)]*)\):\s*')
        match = template.match(line)
        if match.group(1):
            yield Params(match.group(1).split(','))
        elif not match:
            raise Exception('Bad template def: %s' % line)
        yield from Params.parse_text_or_code(lines)

    @staticmethod
    def parse_text_or_code(lines):
        while lines and not lines[0].strip():
            lines.pop(0)
        if lines:
            if lines[0].strip() == QUOTES:
                yield from Text.parse(lines[1:])
            else:
                yield from Code.parse(lines)


class Text(TextToken):

    def expand(self, tokens):
        self._text = '\n'.join(self._expand_line(line, tokens) for line in self.strip().splitlines())

    def _expand_line(self, line, tokens):
        if line == '$contents':
            return self._contents(tokens)
        else:
            return line

    def _contents(self, tokens):
        sections = []
        for token in tokens:
            if isinstance(token, Text):
                for line in token.strip().splitlines():
                    if line.startswith('## '):
                        title = line[3:].strip()
                        sections.append('* [%s](%s)' % (title, title.replace(' ', '-')))
        return '\n'.join(sections)

    @staticmethod
    def parse(lines):
        text = Text(4)
        while lines and lines[0].strip() != QUOTES:
            text.append(lines.pop(0))
        if text:
            yield text
        if lines:
            yield from Params.parse_text_or_code(lines[1:])


class Code(TextToken):

    def to_cell(self):
        return nbv.new_code_cell(self.strip())

    @staticmethod
    def parse(lines):
        code = Code(4)
        while lines and lines[0].strip() != QUOTES:
            code.append(lines.pop(0))
        if code:
            yield code
        if lines:
            yield from Params.parse_text_or_code(lines)


class Import(Code):

    @staticmethod
    def parse(lines):
        imports = Import(0)
        while lines:
            if lines[0].startswith('def '):
                if imports:
                    yield imports
                yield from Params.parse(lines)
                return
            else:
                imports.append(lines.pop(0))


def tokenize(text):
    yield from Import.parse(list(text.splitlines()))


def load(name):
    template = getattr(__import__('ch2.uranus.template', fromlist=[name]), name)
    return getsource(template)


if __name__ == '__main__':
    tokens = list(tokenize(load('compare_activities')))
    print(tokens)
    notebook = Token.to_notebook(tokens)
    nb.write(notebook, stdout)