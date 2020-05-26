from logging import getLogger

from sqlalchemy import intersect, or_

from .args import QUERY, SUB_COMMAND, ACTIVITIES, SHOW, SET
from ..config.config import NOTES
from ..data.constraint import constraint, check_constraint, activity_conversion, constrained_sources, sort_groups, \
    group_by_type
from ..diary.model import DB, VALUE, UNITS, TEXT
from ..lib import time_to_local_time
from ..names import N
from ..pipeline.calculate.activity import ActivityCalculator
from ..sql import ActivityTopicJournal, FileHash, ActivityJournal, StatisticJournal, ActivityTopicField, \
    ActivityTopic, StatisticJournalText, StatisticName

log = getLogger(__name__)


def search(args, system, db):
    '''
## search

    > ch2 search [-a|--advanced] QUERY [--show NAME ...] [--set NAME=VALUE]

This searches for sources.
Sources are typically activities, but also include monitor data, diary journal entries, etc.
The search finds sources that match all the conditions (each source, individually).
So testing for activity distance and activity time is reasonable - both are associated with an activity
and some activities may meet both conditions.
But comparing steps walked - monitor data - with distance cycled - activity data - will always fail to match
because no source contains both monitor and activity data.

Once a source activity is found additional statistics from that source be displayed (--show)
and a single value modified (--set).

Simple searches (without --advanced) look for matches of all given words in the
name and notes fields for the activity.

The advanced syntax is similar to SQL, but element names are statistic names.
A name has the format "Owner.name:group" where the owner and group are optional.
The name can also include SQL wildcards (eg "%fitness%").

A source is associated with a single activity group, so any group qualification will restrict the results
to sources with that activity group (and giving two different groups will fail to match any source).
If no owner or group is given then all possible values are considered.

The owner of a name is the process that calculated the value.
It works as a kind of "namespace" - the database could contain multiple statistics called "active_distance"
but only one will have been calculated by ActivityCalculator.

For advanced searches string values must be quoted, negation and NULL values are not supported,
and comparison must be between a name and a value (not two names).

### Examples

    > ch2 search text bournmouth

Find any activities where the text mentions Bournmouth.

    > ch2 search sources 'name="Wrong Name"' --set 'name="Right Name"'

Modify the name variable.

    > ch2 search activities 'ActivityCalculator.active_distance:mtb > 10 and active_time < 3600'

Find mtb activities that cover over 10km in under an hour.
    '''
    cmd, query = args[SUB_COMMAND], ' '.join(args[QUERY])
    with db.session_context() as s:
        if cmd == TEXT:
            process_results(text_search(s, query))
        else:
            conversion = activity_conversion if cmd == ACTIVITIES else None
            process_results(constrained_sources(s, query, conversion=conversion),
                            show=args[SHOW], set=args[SET])


def text_search(s, query):
    pass


def process_results(sources, show=None, set=None):
    groups = sort_groups(group_by_type(sources))
    for type in groups:
        print(type.__name__, ':')
        for source in groups[type]:
            print('  ', source.long_str())


def expand_activities(s, activities):
    return [expand_activity(s, activity) for activity in activities]


def expand_activity(s, activity_journal):
    topic_journal = s.query(ActivityTopicJournal). \
        join(FileHash).join(ActivityJournal). \
        filter(ActivityJournal.id == activity_journal.id).one()

    def format(statistic):
        if statistic:
            return {VALUE: statistic.value, UNITS: statistic.statistic_name.units}
        else:
            return None

    def value(statistic):
        if statistic:
            return statistic.value
        else:
            return None

    return {DB: activity_journal.id,
            'name': {VALUE: value(StatisticJournal.for_source(s, topic_journal.id, N.NAME,
                                                            ActivityTopic, activity_journal.activity_group)),
                   UNITS: None},
            'group': {VALUE: activity_journal.activity_group.name, UNITS: None},
            'start': {VALUE: time_to_local_time(activity_journal.start), UNITS: 'date'},
            'time': format(StatisticJournal.for_source(s, activity_journal.id, N.ACTIVE_TIME,
                                                       ActivityCalculator, activity_journal.activity_group)),
            'distance': format(StatisticJournal.for_source(s, activity_journal.id, N.ACTIVE_DISTANCE,
                                                           ActivityCalculator, activity_journal.activity_group))}


def display(data):
    if data:
        value = data[0].formatted()
        if len(data) > 1: value += '...'
        return value
    else:
        return '-'


def parse_set(s, set):
    name, op, value = constraint(set)[0]
    if op != '=': raise Exception(f'{set} must be simple assignment')
    check_constraint(s, (name, op, value))
    return name, value


def process_activities(s, activities, show, set):
    if set:
        name, value = parse_set(s, set)
    for activity in activities:
        print(f'{display(activity.get_named(s, N.START, owner=ActivityCalculator))}  '
              f'{activity.activity_group.name}  '
              f'{display(activity.get_all_named(s, N.NAME, owner=ActivityTopic))}')
        for qname in show:
            for result in activity.get_all_named(s, qname):
                print(f'  {result.statistic_name.name} = {result.formatted()}')
        if set:
            for result in activity.get_all_named(s, name):
                before = result.formatted()
                result.set(value)
                after = result.formatted()
                log.info(f'  {result.statistic_name}: {before!r} -> {after!r}')


def parse(query):
    word, quote = '', None
    for c in query:
        if c == ' ':
            if quote:
                word += c
            else:
                if word:
                    yield word
                    word = ''
        elif c == quote:
            quote = None
            yield word
            word = ''
        elif not word and c in ('"', "'"):
            quote = c
        else:
            word += c
    if quote:
        raise Exception('Unbalanced quote')
    if word:
        yield word


def word_query(s, ids, word):
    return s.query(StatisticJournalText.source_id). \
        filter(StatisticJournalText.statistic_name_id.in_(ids),
               StatisticJournalText.value.ilike('%' + word + '%'))


def simple_activity_search(s, query):
    words = list(parse(query))
    log.debug(f'Parsed {query} as {words}')
    words_query = None
    ids = [id[0] for id in s.query(StatisticName.id).
        filter(StatisticName.name.in_([NOTES, N.NAME]),
               StatisticName.owner == ActivityTopic).all()]
    for word in words:
        if words_query is not None:
            words_query = intersect(words_query, word_query(s, ids, word)).select()
        else:
            words_query = word_query(s, ids, word)
    q = s.query(ActivityJournal). \
        join(FileHash). \
        join(ActivityTopicJournal). \
        filter(or_(ActivityJournal.id.in_(words_query),
                   ActivityTopicJournal.id.in_(words_query)))
    log.debug(q)
    return q.all()
