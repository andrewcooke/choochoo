import datetime as dt
from logging import getLogger

from .args import QUERY, SUB_COMMAND, ACTIVITIES, SHOW, SET, mm, SOURCES
from ..data.constraint import activity_conversion, constrained_sources, sort_groups, \
    group_by_type
from ..diary.model import TEXT
from ..lib import to_time, to_date

log = getLogger(__name__)


def search(args, system, db):
    '''
## search

    > ch2 search text QUERY [--show NAME ...] [--set NAME=VALUE]
    > ch2 search activities QUERY [--show NAME ...] [--set NAME=VALUE]
    > ch2 search sources QUERY [--show NAME ...] [--set NAME=VALUE]

Search the database.

The first form (search text) searches for the given text in activity name and description.

The second form (search activities) is similar, but allows for more complex searches (similar to SQL)
that target particular fields.

The third form (search sources) looks for matches for any source (not just activities).

Note that 'search activities' treats both activity journals and activity topics (ie data from FIT
files and data entered by the user) as a single 'source', while 'search activities' treats each source
as separate.

Once a result is found additional statistics from that source be displayed (--show)
and a single value modified (--set).

The search syntax (for activities and sources) is similar to SQL, but element names are statistic names.
A name has the format "Owner.name:group" where the owner and group are optional.
The name and group also include SQL wildcards (eg "%fitness%").

The owner of a name is the process that calculated the value.
It works as a kind of "namespace" - the database could contain multiple statistics called "active_distance"
but only one will have been calculated by ActivityCalculator.

For complex searches, string values must be quoted, negation and NULL values are not supported,
and comparison must be between a name and a value (not two names).

### Examples

    > ch2 search text bournemouth

Find any activities where the text mentions Bournemouth.

    > ch2 search sources 'name="Wrong Name"' --set 'name="Right Name"'

Modify the name variable.

    > ch2 search activities 'ActivityCalculator.active_distance:mtb > 10 and active_time < 3600'

Find mtb activities that cover over 10km in under an hour.
    '''
    if args[SHOW] and args[SET]:
        raise Exception(f'Give at most one of {mm(SHOW)} and {mm(SET)}')
    cmd = args[SUB_COMMAND]
    with db.session_context() as s:
        if cmd == TEXT:
            query = ' and '.join([f'(ActivityTopic.name = "{word}" or ActivityTopic.notes = "{word}")'
                                  for word in args[QUERY]])
            conversion = activity_conversion
        else:
            query = ' '.join(args[QUERY])
            if cmd == ACTIVITIES:
                conversion = activity_conversion
            else:
                conversion = None
        results = constrained_sources(s, query, conversion=conversion)
        process_results(s, results, show=args[SHOW], set=args[SET], activity=bool(conversion))


def text_search(s, words):
    query = ' and '.join([f'(ActivityTopic.name = "{word}" or ActivityTopic.notes = "{word}")'
                          for word in words])
    return constrained_sources(s, query, activity_conversion)


def process_results(s, sources, show=None, set=None, activity=False):
    groups = sort_groups(group_by_type(sources))
    for type in groups:
        print(f'\n{type.__name__}:')
        if show:
            show_results(s, groups[type], show, activity)
        elif set:
            set_results(s, groups[type], set, activity)
        else:
            for source in groups[type]:
                print('  ', source.long_str())
    if show:
        print()


def show_results(s, sources, show, activity):
    for i, source in enumerate(sources, start=1):
        for qname in show:
            if qname.startswith('.'):
                cls = source.__class__.__name__
                try:
                    value = getattr(source, qname[1:])
                    print(f'{i:03d}  {cls}{qname} {value}')
                except AttributeError:
                    print(f'{i:03d}  {cls}{qname} not present')
            else:
                if activity:
                    journals = source.get_all_qname(s, qname)
                else:
                    journals = source.get_qname(s, qname)
                for journal in journals:
                    warning = 'TIME SERIES ' if journal.serial is not None else ''
                    owner = journal.statistic_name.owner
                    name = journal.statistic_name.name
                    group = journal.source.activity_group.name if journal.source.activity_group else 'none'
                    print(f'{i:03d}  {warning}{owner}.{name}:{group} {journal.value}')


def set_results(s, sources, set, activity):
    name, value = set.split('=')
    name = name.strip()
    value = value.strip()
    for source in sources:
        if name.startswith('.'):
            instance, attr = source, name[1:]
        else:
            if activity:
                instance, attr = source.get_all_qname(s, name), 'value'
            else:
                instance, attr = source.get_qname(s, name), 'value'
            if not instance: raise Exception(f'{name} not found')
            if len(instance) > 1: raise Exception(f'{name} ambiguous')
            instance = instance[0]
        print(f'{instance}.{attr} <- {value}')
        current = getattr(instance, attr)
        if isinstance(current, int): value = int(value)
        elif isinstance(current, float): value = float(value)
        else: value = drop_quotes(value)
        # don't convert times - let the type handle conversion
        setattr(instance, attr, value)


def drop_quotes(value):
    if len(value) > 1 and value[0] == '"' and value[-1] == '"': value = value[1:-1]
    elif len(value) > 1 and value[0] == "'" and value[-1] == "'": value = value[1:-1]
    return value
