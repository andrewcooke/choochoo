
import datetime as dt
from logging import getLogger
from re import escape

from sqlalchemy import union, intersect, or_, not_

from ..lib import local_time_to_time
from ..lib.peg import transform, choice, pattern, sequence, Recursive, drop, exhaustive, single
from ..lib.utils import timing
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
    with timing('parse AST'):
        ast = constraint(query)[0]
    log.debug(f'AST: {ast}')
    with timing('check AST'):
        check_constraints(s, ast)
    log.debug('Checked constraints')
    with timing('build SQL'):
        q = build_activity_query(s, ast)
    log.debug(f'Query: {q}')
    with timing('execute SQL'):
        return q.all()


def check_constraints(s, ast):
    l, op, r = ast
    if op in (AND, OR):
        check_constraints(s, l)
        check_constraints(s, r)
    else:
        check_constraint(s, ast)


def infer_types(value):
    if isinstance(value, str): return [StatisticJournalType.TEXT]
    if isinstance(value, dt.datetime): return [StatisticJournalType.TIMESTAMP]
    return [StatisticJournalType.FLOAT, StatisticJournalType.INTEGER]


def check_constraint(s, ast):
    qname, op, value = ast
    name, group = parse_qname(qname)
    q = s.query(StatisticName.id). \
        filter(StatisticName.name.ilike(name),
               StatisticName.statistic_journal_type.in_(infer_types(value)))
    if group:
        q = q.join(ActivityGroup).filter(ActivityGroup.name.ilike(group))
    if not q.count():
        raise Exception(f'No match for statistic {qname} with type {value.__class__.__name__}')
    if not s.query(StatisticJournal). \
            join(Source). \
            filter(StatisticJournal.statistic_name_id.in_(q),
                   Source.type.in_([SourceType.ACTIVITY, SourceType.ACTIVITY_TOPIC])).count():
        raise Exception(f'Statistic {qname} exists but is not associated with any activity data')


def build_activity_query(s, ast):
    constraints = build_constraints(s, ast).cte()
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
    qname, op, value = ast
    name, group = parse_qname(qname)
    if isinstance(value, str):
        return get_activity_journal_ids(s, name, op, value, group,
                                        StatisticJournalType.TEXT, {'=': 'ilike', '!=': 'nlike'})
    elif isinstance(value, dt.datetime):
        return get_activity_journal_ids(s, name, op, value, group, StatisticJournalType.TIMESTAMP)
    else:
        qint = get_activity_journal_ids(s, name, op, value, group, StatisticJournalType.INTEGER)
        qfloat = get_activity_journal_ids(s, name, op, value, group, StatisticJournalType.FLOAT)
        return union(qint, qfloat).select()


def get_activity_journal_ids(s, name, op, value, group, type, update_attrs=None):
    statistic_journals = \
        get_statistic_journals(s, name, op, value, group, type, update_attrs=update_attrs).cte()
    via_activity_journal = s.query(ActivityJournal.id). \
        join(statistic_journals, ActivityJournal.id == statistic_journals.c.source_id)
    if group is None:
        via_activity_journal = \
            via_activity_journal.filter(ActivityJournal.activity_group_id == statistic_journals.c.activity_group_id)
    via_topic_journal = s.query(ActivityJournal.id). \
        join(ActivityTopicJournal, ActivityTopicJournal.file_hash_id == ActivityJournal.file_hash_id). \
        join(statistic_journals, ActivityTopicJournal.id == statistic_journals.c.source_id)
    if group is None:
        via_topic_journal = \
            via_topic_journal.filter(ActivityJournal.activity_group_id == statistic_journals.c.activity_group_id)
    return union(via_activity_journal, via_topic_journal).select()


def get_statistic_journals(s, name, op, value, group, type, update_attrs=None):
    attrs = {'=': '__eq__', '!=': '__ne__', '>': '__gt__', '>=': '__ge__', '<': '__lt__', '<=': '__le__'}
    if update_attrs:
        attrs.update(update_attrs)
    attr = attrs[op]
    statistic_journal = STATISTIC_JOURNAL_CLASSES[type]
    q = s.query(statistic_journal.source_id, StatisticName.activity_group_id). \
        join(StatisticName). \
        filter(StatisticName.name.ilike(name))
    if attr == 'nlike':  # no way to negate like in a single attribute
        q = q.filter(not_(statistic_journal.value.ilike(value)))
    else:
        q = q.filter(getattr(statistic_journal.value, attr)(value))
    if group:
        q = q.join(ActivityGroup).filter(ActivityGroup.name.ilike(group))
    return q


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
