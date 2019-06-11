
from re import escape

from sqlalchemy import select, or_, and_

from ch2.squeal import ActivityJournal, StatisticName
from .frame import _tables
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


def flip(l):
    value, op, name = l[0]
    return [(name, {'=': '=', '!=': '!=', '<': '>', '>': '<', '>=': '<=', '<=': '>='}[op], value)]


name = pat(r'(\w(?:\s*\w)*)')

number = choice(pat(r'(-?\d+)', int), pat(r'([-+]?\d*\.?\d+)(?:[eE]([-+]?\d+))?', unexp))

string = choice(pat(r'"((?:[^"\\]|\\.)*)"'), pat(r"'((?:[^'\\]|\\.)*)'"))

value = choice(number, string)

operator = choice(*[lit(cmp) for cmp in ['=', '!=', '<', '>', '<=', '>=']])

comparison = choice(join(name, operator, value), transform(join(value, operator, name), flip))

term = Recursive()

and_comparison = Recursive()
and_comparison.calls(choice(term, join(term, lit('&'), term)))

or_comparison = Recursive()
or_comparison.calls(choice(and_comparison, join(and_comparison, lit('|'), or_comparison)))

parens = transform(sequence(drop(lit('(')), or_comparison, drop(lit(')'))))

term.calls(choice(comparison, parens))

constraint = exhaustive(choice(or_comparison, parens))


# def build_activity_query(s, ast):
#     t = _tables()
#     constraints = build_constraints(t, ast)
#     return s.query(ActivityJournal).filter(ActivityJournal.id.in_(constraints))
#
#
# def build_constraints(s, t, ast):
#     l, op, r = ast
#     if op in '&|':
#         lcte = build_constraints(s, t, l)
#         rcte = build_constraints(s, t, r)
#         return build_join(t, op, lcte, rcte)
#     else:
#         return build_comparison(s, t, ast)
#
#
# def build_join(t, op, lcte, rcte):
#     if op == '|':
#         return select([t.aj.c.id]).where(or_(t.aj.c.id.in_(lcte), t.aj.c.id.in_(rcte)))
#     else:
#         return select([t.aj.c.id]).where(and_(t.aj.c.id.in_(lcte), t.aj.c.id.in_(rcte)))
#
#
# def build_comparison(s, t, ast):
#     name, op, value = ast
#     stat = s.query(StatisticName).filter(StatisticName.name)
