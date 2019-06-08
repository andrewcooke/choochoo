
from re import escape

from ..lib.peg import transform, choice, pattern, sequence, Recursive, drop, exhaustive


def pat(regexp, trans=None):
    parser = pattern(r'\s*' + regexp + r'\s*')
    if trans:
        parser = transform(parser, trans)
    return parser


def lit(text, trans=None):
    return pat('(' + escape(text) + ')', trans=trans)


def unexp(values):
    try:
        val, exp = values
        return [float(val) * 10 ** int(exp)]
    except:
        return [float(values[0])]


def to_tuple(l):
    return [tuple(l)]


def join(a, sep, b):
    return transform(sequence(a, sep, b), to_tuple)


name = pat(r'(\w+)')

number = choice(pat(r'(-?\d+)', int), pat(r'([-+]?\d*\.?\d+)(?:[eE]([-+]?\d+))?', unexp))

string = choice(pat(r'"((?:[^"\\]|\\.)*)"'), pat(r"'((?:[^'\\]|\\.)*)'"))

value = choice(number, string)

operator = choice(*[lit(cmp) for cmp in ['=', '!=', '<', '>', '<=', '>=']])

comparison = choice(join(name, operator, value), join(value, operator, name))

term = Recursive()

and_comparison = Recursive()
and_comparison.calls(choice(term, join(term, lit('&'), term)))

or_comparison = Recursive()
or_comparison.calls(choice(and_comparison, join(and_comparison, lit('|'), or_comparison)))

parens = transform(sequence(drop(lit('(')), or_comparison, drop(lit(')'))))

term.calls(choice(comparison, parens))

constraint = exhaustive(choice(or_comparison, parens))
