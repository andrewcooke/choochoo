
import datetime as dt
from collections import defaultdict
from logging import getLogger
from re import escape

from sqlalchemy import union, intersect, not_

from ..lib import local_time_to_time
from ..lib.peg import transform, choice, pattern, sequence, Recursive, drop, exhaustive, single
from ..lib.utils import timing
from ..sql import ActivityJournal, StatisticName, StatisticJournalType, ActivityGroup, StatisticJournal, \
    ActivityTopicJournal, Source, FileHash
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
# no wildcards in group (no use case)
name = pat(r'((?:[A-Z%][A-Za-z0-9_%]*\.)?[a-z%][a-z0-9_%]*(?::[a-z][a-z0-9_]*)?)')
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


def constrained_sources(s, query, conversion=None):
    with timing('parse AST'):
        ast = constraint(query)[0]
    log.debug(f'AST: {ast}')
    with timing('check AST'):
        check_constraints(s, ast)
    log.debug('Checked constraints')
    with timing('build SQL'):
        q = build_source_query(s, ast, conversion=conversion)
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
    owner, name, group = parse_qualified_name(qname)
    q = s.query(StatisticName.id). \
        filter(StatisticName.name.like(name),
               StatisticName.statistic_journal_type.in_(infer_types(value)))
    if owner: q = q.filter(StatisticName.owner.like(owner))
    if not q.count():
        raise Exception(f'No match for statistic {qname} for type {value.__class__.__name__}')


def build_source_query(s, ast, conversion=None):
    constraints = build_constraints(s, ast, conversion=conversion).cte()
    return s.query(Source).filter(Source.id.in_(constraints))


def build_constraints(s, ast, conversion=None):
    l, op, r = ast
    if op in (AND, OR):
        lcte = build_constraints(s, l, conversion=conversion)
        rcte = build_constraints(s, r, conversion=conversion)
        return build_join(op, lcte, rcte)
    else:
        constraint = build_comparisons(s, ast)
        if conversion: constraint = conversion(s, constraint)
        return constraint


def build_join(op, lcte, rcte):
    if op == OR:
        return union(lcte, rcte).select()
    else:
        return intersect(lcte, rcte).select()


def build_comparisons(s, ast):
    qname, op, value = ast
    owner, name, group = parse_qualified_name(qname)
    if isinstance(value, str):
        return get_source_ids(s, owner, name, op, value, group,
                              StatisticJournalType.TEXT, {'=': 'ilike', '!=': 'nlike'})
    elif isinstance(value, dt.datetime):
        return get_source_ids(s, owner, name, op, value, group, StatisticJournalType.TIMESTAMP)
    else:
        qint = get_source_ids(s, owner, name, op, value, group, StatisticJournalType.INTEGER)
        qfloat = get_source_ids(s, owner, name, op, value, group, StatisticJournalType.FLOAT)
        return union(qint, qfloat).select()


def get_source_ids(s, owner, name, op, value, group, type, update_attrs=None):
    attrs = {'=': '__eq__', '!=': '__ne__', '>': '__gt__', '>=': '__ge__', '<': '__lt__', '<=': '__le__'}
    if update_attrs:
        attrs.update(update_attrs)
    attr = attrs[op]
    statistic_journal = STATISTIC_JOURNAL_CLASSES[type]
    q = s.query(Source.id). \
        join(statistic_journal). \
        join(StatisticName). \
        filter(StatisticName.name.like(name))
    if owner:
        q = q.filter(StatisticName.owner.like(owner))
    if group:
        q = q.join(ActivityGroup).filter(ActivityGroup.name.ilike(group))
    if attr == 'nlike':  # no way to negate like in a single attribute
        q = q.filter(not_(statistic_journal.value.ilike(value)))
    else:
        q = q.filter(getattr(statistic_journal.value, attr)(value))
    return q


def parse_qualified_name(qname):
    if ':' in qname:
        left, group = qname.rsplit(':', 1)
    else:
        left, group = qname, None
    if '.' in left:
        owner, name = left.split('.', 1)
    else:
        owner, name = None, left
    log.debug(f'Parsed {qname} as {owner}.{name}:{group}')
    return owner, name, group


def activity_conversion(s, source_ids):
    # convert the query that gives any source id and select either those that are activities directly,
    # or activities associated with a topic (eg user entered activity notes)
    source_ids = source_ids.cte()
    q_direct = s.query(ActivityJournal.id). \
        filter(ActivityJournal.id.in_(source_ids))
    q_via_topic = s.query(ActivityJournal.id). \
        join(FileHash). \
        join(ActivityTopicJournal). \
        filter(ActivityTopicJournal.id.in_(source_ids))
    return union(q_direct, q_via_topic).select()


def group_by_type(sources):
    groups = defaultdict(list)
    for source in sources:
        groups[type(source)].append(source)
    return groups


def sort_sources(sources):
    def key(source):
        for attr in 'start', 'time', 'id':
            if hasattr(source, attr):
                return getattr(source, attr)
    return sorted(sources, key=key)


def sort_groups(groups):
    return {key: sort_sources(values) for key, values in groups.items()}
