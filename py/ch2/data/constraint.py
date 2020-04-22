
import datetime as dt
from logging import getLogger
from re import escape

from sqlalchemy import union, intersect, or_

from ..lib import local_time_to_time
from ..lib.peg import transform, choice, pattern, sequence, Recursive, drop, exhaustive, single
from ..sql import ActivityJournal, StatisticName, StatisticJournalType, ActivityGroup, StatisticJournal, FileHash, \
    ActivityTopicJournal, StatisticJournalText, Source
from ..sql.tables.source import SourceType
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
    qname, op, value = ast
    name, group = parse_qname(qname)
    if isinstance(value, str):
        q = get_journal_source_id(s, name, op, value, StatisticJournalType.TEXT, {'=': 'ilike'})
        return add_group(q, group)
    elif isinstance(value, dt.datetime):
        q = get_journal_source_id(s, name, op, value, StatisticJournalType.TIMESTAMP)
        return add_group(q, group)
    else:
        qint = get_journal_source_id(s, name, op, value, StatisticJournalType.INTEGER)
        qint = add_group(qint, group)
        qfloat = get_journal_source_id(s, name, op, value, StatisticJournalType.FLOAT)
        qfloat = add_group(qfloat, group)
        return union(qint, qfloat).select()


def get_journal_source_id(s, name, op, value, type, update_attrs=None):
    attrs = {'=': '__eq__', '!=': '__ne__', '>': '__gt__', '>=': '__ge__', '<': '__lt__', '<=': '__le__'}
    if update_attrs:
        attrs.update(update_attrs)
    attr = attrs[op]
    journal = STATISTIC_JOURNAL_CLASSES[type]
    return s.query(journal.source_id). \
        join(StatisticName). \
        filter(StatisticName.name.ilike(name),
               getattr(journal.value, attr)(value))


def add_group(q, group):
    if group:
        return q.join(ActivityGroup, StatisticName.activity_group_id == ActivityGroup.id). \
            filter(ActivityGroup.name.ilike(group))
    elif group is None:
        return q
    else:
        qaj = q.join(ActivityJournal). \
            filter(ActivityJournal.id == StatisticJournal.source_id,
                   ActivityJournal.activity_group_id == StatisticName.activity_group_id)
        qatj = q.join(ActivityTopicJournal). \
            join(FileHash, ActivityTopicJournal.file_hash_id == FileHash.id). \
            join(ActivityJournal, ActivityJournal.file_hash_id == FileHash.id). \
            filter(ActivityTopicJournal.id == StatisticJournal.source_id,
                   ActivityJournal.activity_group_id == StatisticName.activity_group_id)
        return union(qaj, qatj).select()


def parse_qname(qname):
    '''
    A qualified name (for a statistic) has the form NAME:GROUP with optional spaces where:

    NAME (with no qualifier) means 'match the group of the current activity' - returned as None
    NAME: (colon but no value) means 'match any constraint' - returned as ''
    NAME:GROUP means 'match the given group' - returned as the name
    '''
    if ':' in qname:
        name, group = qname.split(':')
        name, group = name.strip(), group.strip()
    else:
        name, group = qname.strip(), None
    log.debug(f'Parsed {qname} as {name}:{group}')
    return name, group
