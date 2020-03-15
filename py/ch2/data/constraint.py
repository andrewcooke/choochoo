
from re import escape

from sqlalchemy import select, or_, and_, union

from .frame import _tables
from ..lib.peg import transform, choice, pattern, sequence, Recursive, drop, exhaustive, single
from ..sql import ActivityJournal, StatisticName, StatisticJournalType


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

constraint = single(exhaustive(choice(or_comparison, parens)))


def constrained_activities(s, query):
    ast = constraint(query)[0]
    q = build_activity_query(s, ast)
    return list(q)


def build_activity_query(s, ast):
    t = _tables()
    constraints = build_constraints(s, t, ast)
    return s.query(ActivityJournal).filter(ActivityJournal.id.in_(constraints)).order_by(ActivityJournal.start)


def build_constraints(s, t, ast):
    l, op, r = ast
    if op in '&|':
        lcte = build_constraints(s, t, l)
        rcte = build_constraints(s, t, r)
        return build_join(t, op, lcte, rcte)
    else:
        return build_comparisons(s, t, ast)


def build_join(t, op, lcte, rcte):
    if op == '|':
        return select([t.aj.c.id]).where(or_(t.aj.c.id.in_(lcte), t.aj.c.id.in_(rcte)))
    else:
        return select([t.aj.c.id]).where(and_(t.aj.c.id.in_(lcte), t.aj.c.id.in_(rcte)))


def build_comparisons(s, t, ast):
    name, op, value = ast
    comparisons = [build_comparison(t, statistic_name, op, value)
                   for statistic_name in s.query(StatisticName).filter(StatisticName.name == name).all()]
    if len(comparisons) == 1:
        return comparisons[0]
    else:
        return union(*comparisons)


def build_comparison(t, statistic_name, op, value):
    if statistic_name.statistic_journal_type == StatisticJournalType.INTEGER:
        table = t.sji
    elif statistic_name.statistic_journal_type == StatisticJournalType.FLOAT:
        table = t.sjf
    else:
        table = t.sjs
    q = select([t.sj.c.source_id]).select_from(t.sj.join(table)).where(t.sj.c.statistic_name_id == statistic_name.id)
    attr = {'=': '__eq__', '!=': '__ne__', '>': '__gt__', '>=': '__ge__', '<': '__lt__', '<=': '__le__'}[op]
    q = q.where(getattr(table.c.value, attr)(value))
    return q
