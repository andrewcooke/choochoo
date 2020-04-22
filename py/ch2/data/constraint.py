
import datetime as dt
from logging import getLogger
from re import escape

from sqlalchemy import select, union, intersect, or_

from ..lib import local_time_to_time
from ..lib.peg import transform, choice, pattern, sequence, Recursive, drop, exhaustive, single
from ..sql import ActivityJournal, StatisticName, StatisticJournalType, ActivityGroup, StatisticJournal, FileHash, \
    ActivityTopicJournal
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


AND, OR = 'and', 'or'
name = pat(r'(\w(?:\s*\w)*(?::(?:\w(?:\s*\w)*)?)?)')
# important that the different value types are exclusive to avoid ambiguities
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
and_comparison.calls(choice(term, join(term, lit(AND), and_comparison)))

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
    return q.all()


def build_activity_query(s, ast):
    constraints = build_constraints(s, ast).cte()
    return s.query(ActivityJournal). \
        join(FileHash). \
        join(ActivityTopicJournal). \
        filter(or_(ActivityJournal.id.in_(constraints),
                   ActivityTopicJournal.id.in_(constraints))). \
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
    # TODO _ brokwn
    name, op, value = ast
    if ':' in name:
        sname, gname = name.split(':', 1)
        if gname.lower() in ('none', 'null'):
            statistic_names = s.query(StatisticName). \
                filter(StatisticName.name.ilike(sname),
                       StatisticName.activity_group == None).all()
        else:
            activity_groups = s.query(ActivityGroup).filter(ActivityGroup.name.ilike(gname)).all()
            if not activity_groups:
                raise Exception(f'No activity group matches {gname}')
            statistic_names = s.query(StatisticName). \
                filter(StatisticName.name.ilike(sname),
                       StatisticName.activity_group.in_(activity_groups)).all()
        if not statistic_names:
            raise Exception(f'No statistic name matches {name}')
        comparisons = [build_comparison_orm(statistic_name, op, value) for statistic_name in statistic_names]
    else:
        log.warning(f'{name} is unconstrained (to restrict to a particular group use {name}:Group)')
        comparisons = [build_comparison_sql(s, name, op, value)]
    if len(comparisons) == 1:
        return comparisons[0]
    else:
        return union(*comparisons).select()


def check_column(statistic_name, op, value):
    table = STATISTIC_JOURNAL_CLASSES[statistic_name.statistic_journal_type].__table__
    sj = StatisticJournal.__table__
    attr = {'=': '__eq__', '!=': '__ne__', '>': '__gt__', '>=': '__ge__', '<': '__lt__', '<=': '__le__'}[op]
    if statistic_name.statistic_journal_type == StatisticJournalType.TIMESTAMP:
        if not isinstance(value, dt.datetime):
            raise Exception(f'{statistic_name.name} is a timestamp, but {value} is not a date')
        column = sj.c.time
    elif statistic_name.statistic_journal_type == StatisticJournalType.TEXT:
        if not isinstance(value, str):
            raise Exception(f'{statistic_name.name} is textual, but {value} is not a string')
        column = table.c.value
        if op == '=': attr = 'ilike'
    else:
        if not (isinstance(value, int) or isinstance(value, float)):
            raise Exception(f'{statistic_name.name} is numerical, but {value} is not a number')
        column = table.c.value
    return sj, table, attr, column


def build_comparison_orm(statistic_name, op, value):
    sj, table, attr, column = check_column(statistic_name, op, value)
    log.debug(f'{statistic_name} ({statistic_name.id}) {attr} {value!r}')
    return select([sj.c.source_id]). \
        select_from(sj.join(table)). \
        where(sj.c.statistic_name_id == statistic_name.id). \
        where(getattr(column, attr)(value))


def build_comparison_sql(s, name, op, value):
    statistic_names = s.query(StatisticName).filter(StatisticName.name.ilike(name)).all()
    if not statistic_names: raise Exception(f'No statistic name matches {name}')
    statistic_types = set(statistic_name.statistic_journal_type for statistic_name in statistic_names)
    if len(statistic_types) > 1:
        for statistic_name in statistic_names: log.debug(f'{statistic_name}')
        raise Exception(f'{name} matches multiple statistics with different types; '
                        f'use a more specific name ({name}:group)')
    sj, table, attr, column = check_column(statistic_names[0], op, value)
    sn = StatisticName.__table__
    return select([sj.c.source_id]). \
        select_from(sj.join(table).join(sn)). \
        where(sn.c.name.ilike(name)). \
        where(getattr(column, attr)(value))


def parse_qname(qname):
    '''A qualified name (for a statistic) has the form NAME:GROUP with optional spaces where:

    NAME (with no qualifier) means 'match any constraint'
    NAME: (colon but no value) means 'match the group of the current activity'
    NAME:null or NAME:none (any case) means 'match a constraint of None'
    NAME:GROUP means 'match the given group'

    This code returns (name, group) where group is False, True and None for the first three cases above, respectively.
    '''
    if ':' in qname:
        name, group = qname.split(':')
        name, group = name.strip(), group.strip()
        if group:
            if group.lower() in ('none', 'null'):
                group = None
        else:
            group = True
    else:
        name, group = qname.strip(), False
    log.debug(f'Parsed {qname} as {name}:{group}')
    return name, group
