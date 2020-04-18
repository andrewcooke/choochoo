
import datetime as dt
from logging import getLogger
from re import escape

from sqlalchemy import select, union, intersect

from ..lib import local_time_to_time
from ..lib.peg import transform, choice, pattern, sequence, Recursive, drop, exhaustive, single
from ..sql import ActivityJournal, StatisticName, StatisticJournalType, ActivityGroup, StatisticJournal
from ..sql.tables.statistic import STATISTIC_JOURNAL_CLASSES

log = getLogger(__name__)


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


AND, OR = '&', '|'
name = pat(r'(\w(?:\s*\w)*(?::(?:\w(?:\s*\w)*)?)?)')
number = choice(pat(r'(-?\d+)', lambda x: [int(i) for i in x]),
                pat(r'(-?\d*\.\d+)', lambda x: [float(i) for i in x]),
                pat(r'(-?\d+\.\d*)', lambda x: [float(i) for i in x]),
                pat(r'([-+]?\d*\.?\d+)[eE]([-+]?\d+)', unexp))
string = choice(pat(r'"((?:[^"\\]|\\.)*)"'), pat(r"'((?:[^'\\]|\\.)*)'"))
date = r'\d{4}-\d{2}-\d{2}'
time = r'\d{2}(?::\d{2}(?::\d{2})?)?'
datetime = pat('(' + date + '(?:[T ]' + time + ')?)', lambda x: [local_time_to_time(t) for t in x])
value = choice(number, string, datetime)

operator = choice(*[lit(cmp) for cmp in ['=', '!=', '<', '>', '<=', '>=']])
comparison = choice(join(name, operator, value), transform(join(value, operator, name), flip))

term = Recursive()

and_comparison = Recursive()
and_comparison.calls(choice(term, join(term, lit(AND), term)))

or_comparison = Recursive()
or_comparison.calls(choice(and_comparison, join(and_comparison, lit(OR), or_comparison)))

parens = transform(sequence(drop(lit('(')), or_comparison, drop(lit(')'))))
term.calls(choice(comparison, parens))

constraint = single(exhaustive(choice(or_comparison, parens)))


def constrained_activities(s, query):
    ast = constraint(query)[0]
    log.debug(f'AST: {ast}')
    q = build_activity_query(s, ast)
    log.debug(f'Query: {q}')
    return list(q)


def build_activity_query(s, ast):
    constraints = build_constraints(s, ast)
    return s.query(ActivityJournal). \
        filter(ActivityJournal.id.in_(constraints)). \
        order_by(ActivityJournal.start)


def build_constraints(s, ast):
    l, op, r = ast
    if op in (AND, OR):
        lcte = build_constraints(s, l)
        rcte = build_constraints(s, r)
        return build_join(op, lcte, rcte)
    else:
        return build_comparisons(s, ast)


def build_join(op, lcte, rcte):
    if op == OR:
        return union(lcte, rcte).select()
    else:
        return intersect(lcte, rcte).select()


def build_comparisons(s, ast):
    name, op, value = ast
    if ':' in name:
        sname, gname = name.split(':', 1)
        if gname.lower() in ('none', 'null'):
            statistic_names = s.query(StatisticName). \
                filter(StatisticName.name.like(sname),
                       StatisticName.constraint == None).all()
        else:
            activity_groups = s.query(ActivityGroup).filter(ActivityGroup.name.like(gname)).all()
            if not activity_groups:
                raise Exception(f'No activity group matches {gname}')
            statistic_names = s.query(StatisticName). \
                filter(StatisticName.name.like(sname),
                       StatisticName.constraint.in_(activity_groups)).all()
    else:
        log.warning(f'{name} is unconstrained (to restrict to a particular group use {name}:Group)')
        statistic_names = s.query(StatisticName).filter(StatisticName.name.like(name)).all()
    if not statistic_names:
        raise Exception(f'No statistic name matches {name}')
    comparisons = [build_comparison(statistic_name, op, value) for statistic_name in statistic_names]
    if len(comparisons) == 1:
        return comparisons[0]
    else:
        return union(*comparisons).select()


def build_comparison(statistic_name, op, value):
    table = STATISTIC_JOURNAL_CLASSES[statistic_name.statistic_journal_type].__table__
    sj = StatisticJournal.__table__
    q = select([sj.c.source_id]).select_from(sj.join(table)).where(sj.c.statistic_name_id == statistic_name.id)
    attr = {'=': '__eq__', '!=': '__ne__', '>': '__gt__', '>=': '__ge__', '<': '__lt__', '<=': '__le__'}[op]
    if statistic_name.statistic_journal_type == StatisticJournalType.TIMESTAMP:
        if not isinstance(value, dt.datetime):
            raise Exception(f'{statistic_name.name} is a timestamp, but {value} is not a date')
        column = sj.c.time
    else:
        column = table.c.value
    q = q.where(getattr(column, attr)(value))
    return q
