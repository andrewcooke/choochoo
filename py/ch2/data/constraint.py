
import datetime as dt
from collections import defaultdict
from logging import getLogger
from re import escape

from sqlalchemy import union, intersect, not_
from sqlalchemy.orm import aliased

from ..lib import local_time_to_time, to_time
from ..lib.peg import transform, choice, pattern, sequence, Recursive, drop, exhaustive, single
from ..lib.utils import timing
from ..common.names import UNDEF
from ..sql import ActivityJournal, StatisticName, StatisticJournalType, ActivityGroup, ActivityTopicJournal, Source, \
    FileHash, StatisticJournal
from ..sql.tables.statistic import STATISTIC_JOURNAL_CLASSES
from ..sql.types import lookup_cls

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


AND, OR, NULL = 'and', 'or', 'null'
# no wildcards in group (no use case)
name = pat(r'((?:(?:[A-Z%][A-Za-z0-9\-%]*)?\.)?[a-z%][a-z0-9\-%]*(?::[a-z][a-z0-9\-]*)?)')
# important that the different value types are exclusive to avoid ambiguities
number = choice(pat(r'(-?\d+)', lambda x: [int(i) for i in x]),
                pat(r'(-?\d*\.\d+)', lambda x: [float(i) for i in x]),
                pat(r'(-?\d+\.\d*)', lambda x: [float(i) for i in x]),
                pat(r'([-+]?\d*\.?\d+)[eE]([-+]?\d+)', unexp))
string = choice(pat(r'"((?:[^"\\]|\\.)*)"'), pat(r"'((?:[^'\\]|\\.)*)'"))
date = r'\d{4}-\d{2}-\d{2}'
time = r'\d{2}(?::\d{2}(?::\d{2})?)?'
datetime = pat('(' + date + '(?: ' + time + ')?)', lambda x: [local_time_to_time(t) for t in x])
utc = pat('(' + date + 'T' + time + ')', lambda x: [to_time(t) for t in x])
null = transform(lit(NULL), lambda x: [None])
value = choice(number, string, datetime, utc, null)

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


def trace(f):
    # help trace source of problems in sql generation
    def wrapper(*args, **kargs):
        result = f(*args, **kargs)
        try:
            sql = result[0]
        except:
            sql = result
        # log.debug(f'{f.__name__}: {sql}')
        return result
    return wrapper


def constrained_sources(s, query, conversion=None):
    with timing('parse AST'):
        ast = constraint(query)[0]
    log.debug(f'AST: {ast}')
    attrs = set()
    with timing('check AST'):
        check_constraints(s, ast, attrs)
    log.debug('Checked constraints')
    with timing('build SQL'):
        q = build_source_query(s, ast, attrs, conversion=conversion)
    log.debug(f'Query: {q}')
    with timing('execute SQL'):
        return q.all()


def check_constraints(s, ast, attrs):
    l, op, r = ast
    if op in (AND, OR):
        check_constraints(s, l, attrs)
        check_constraints(s, r, attrs)
    else:
        check_constraint(s, ast, attrs)


def infer_types(value):
    if value is None: return list(StatisticJournalType)
    if isinstance(value, str): return [StatisticJournalType.TEXT]
    if isinstance(value, dt.datetime): return [StatisticJournalType.TIMESTAMP]
    return [StatisticJournalType.FLOAT, StatisticJournalType.INTEGER]


def check_constraint(s, ast, attrs):
    qname, op, value = ast
    try:
        check_statistic_name(s, qname, value)
        log.debug(f'{qname} is a statistic')
    except Exception as e1:
        try:
            check_source_property(qname, value)
            attrs.add(qname)
            log.debug(f'{qname} is an attribute')
        except Exception as e2:
            log.error(e1)
            log.error(e2)
            raise Exception(f'{qname} {op} {value} could not be validated')


def check_statistic_name(s, qname, value):
    owner, name, _ = StatisticName.parse(qname)
    q = s.query(StatisticName.id). \
        filter(StatisticName.name.like(name),
               StatisticName.statistic_journal_type.in_(infer_types(value)))
    if owner: q = q.filter(StatisticName.owner.like(owner))
    if not q.count():
        raise Exception(f'No match for statistic {qname} for type {value.__class__.__name__}')


def check_source_property(qname, value):
    cls, attr = parse_property(qname)
    # todo - check value type somehow


@trace
def build_source_query(s, ast, attrs, conversion=None):
    constraints = build_constraints(s, ast, attrs, conversion=conversion).cte()
    return s.query(Source).filter(Source.id.in_(constraints))


@trace
def build_constraints(s, ast, attrs, conversion=None):
    l, op, r = ast
    if op in (AND, OR):
        lcte = build_constraints(s, l, attrs, conversion=conversion)
        rcte = build_constraints(s, r, attrs, conversion=conversion)
        return build_join(op, lcte, rcte)
    else:
        constraint, null = build_constraint(s, ast, attrs, bool(conversion))
        if conversion: constraint = conversion(s, constraint, null)
        return constraint


@trace
def build_join(op, lcte, rcte):
    if op == OR:
        return aliased(union(lcte, rcte)).select()
    else:
        return aliased(intersect(lcte, rcte)).select()


@trace
def build_constraint(s, ast, attrs, with_conversion):
    qname, op, value = ast
    if qname in attrs:
        return build_property(s, ast), False
    else:
        return build_comparisons(s, ast, with_conversion)


def build_property(s, ast):
    qname, op, value = ast
    cls, attr = parse_property(qname)
    op_attr = get_op_attr(op, value)
    q = s.query(cls.id)
    if attr == 'nlike':
        q = q.filter(not_(getattr(cls, attr).ilike(value)))
    else:
        q = q.filter(getattr(getattr(cls, attr), op_attr)(value))
    return q


@trace
def build_comparisons(s, ast, with_conversion):
    qname, op, value = ast
    owner, name, group = StatisticName.parse(qname, default_activity_group=UNDEF)
    if value is None:
        if op == '=':
            return get_source_ids_for_null(s, owner, name, group, with_conversion), True
        else:
            return aliased(union(*[get_source_ids(s, owner, name, op, value, group, type)
                                   for type in StatisticJournalType
                                   if type != StatisticJournalType.STATISTIC])).select(), False
    elif isinstance(value, str):
        return get_source_ids(s, owner, name, op, value, group, StatisticJournalType.TEXT), False
    elif isinstance(value, dt.datetime):
        return get_source_ids(s, owner, name, op, value, group, StatisticJournalType.TIMESTAMP), False
    else:
        qint = get_source_ids(s, owner, name, op, value, group, StatisticJournalType.INTEGER)
        qfloat = get_source_ids(s, owner, name, op, value, group, StatisticJournalType.FLOAT)
        return aliased(union(qint, qfloat)).select(), False


def get_op_attr(op, value):
    attrs = {'=': '__eq__', '!=': '__ne__', '>': '__gt__', '>=': '__ge__', '<': '__lt__', '<=': '__le__'}
    if isinstance(value, str): attrs.update({'=': 'ilike', '!=': 'nlike'})
    return attrs[op]


def get_source_ids(s, owner, name, op, value, group, type):
    op_attr = get_op_attr(op, value)
    statistic_journal = STATISTIC_JOURNAL_CLASSES[type]
    q = s.query(Source.id). \
        join(statistic_journal). \
        join(StatisticName). \
        filter(StatisticName.name.like(name))
    if owner:
        q = q.filter(StatisticName.owner.like(owner))
    if group is not UNDEF:
        if group:
            q = q.join(ActivityGroup).filter(ActivityGroup.name.ilike(group))
        else:
            q = q.filter(Source.activity_group_id == None)
    if op_attr == 'nlike':  # no way to negate like in a single attribute
        q = q.filter(not_(statistic_journal.value.ilike(value)))
    else:
        q = q.filter(getattr(statistic_journal.value, op_attr)(value))
    return q


def get_source_ids_for_null(s, owner, name, group, with_conversion):
    q = s.query(StatisticJournal.source_id). \
        join(StatisticName). \
        filter(StatisticName.name.like(name))
    if owner:
        q = q.filter(StatisticName.owner.like(owner))
    if group is not UNDEF:
        if group:
            q = q.join(ActivityGroup).filter(ActivityGroup.name.ilike(group))
        else:
            q = q.join(Source).filter(Source.activity_group_id == None)
    if with_conversion:
        # will invert later (in conversion)
        return q
    else:
        return s.query(Source.id).filter(not_(Source.id.in_(q)))


def parse_property(qname):
    if ':' in qname:
        raise Exception(f'{qname} is not a valid property (contains :)')
    if '.' in qname:
        cls, attr = qname.rsplit('.', 1)
        if not cls: cls = 'Source'
    else:
        cls = 'Source'
        attr = qname
    try:
        clz = lookup_cls(cls)
    except:
        cls = 'ch2.sql.' + cls
        clz = lookup_cls(cls)
    getattr(clz, attr)
    log.info(f'Parsed {qname} as {clz}.{attr}')
    return clz, attr


class Intersect(object):
    pass


@trace
def activity_conversion(s, source_ids, null):
    # convert the query that gives any source id and select either those that are activities directly,
    # or activities associated with a topic (eg user entered activity notes)

    # for most queries, we have some source IDs and we want to know if they are activityjournal ids
    # (which we pass through) or activitytopicjournal ids (in which case we convert to activityjournal).
    source_ids = source_ids.cte()
    q_direct = s.query(ActivityJournal.id). \
        filter(ActivityJournal.id.in_(source_ids))
    q_via_topic = s.query(ActivityJournal.id). \
        join(FileHash). \
        join(ActivityTopicJournal). \
        filter(ActivityTopicJournal.id.in_(source_ids))
    q = aliased(union(q_direct, q_via_topic)).select()

    if null:
        # for 'is null' queries we are really asking if the data are missing (since values are not null constrained)
        # so we find what does exist and then invert it.  that inversion has to happen avter conversion
        return s.query(ActivityJournal.id).filter(not_(ActivityJournal.id.in_(q)))
    else:
        return q


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
