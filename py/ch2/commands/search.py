from logging import getLogger

from sqlalchemy import intersect, or_

from .args import QUERY, SHOW, SET, ADVANCED
from ..config.config import NOTES
from ..data import constrained_activities
from ..data.constraint import constraint, check_constraint
from ..diary.model import DB, VALUE, UNITS
from ..lib import time_to_local_time
from ..sql import ActivityTopicJournal, FileHash, ActivityJournal, StatisticJournal, ActivityTopicField, ActivityTopic, \
    StatisticJournalText, StatisticName
from ..stats.calculate.activity import ActivityCalculator
from ..stats.names import TIME, START, ACTIVE_TIME, DISTANCE, ACTIVE_DISTANCE, GROUP

log = getLogger(__name__)

name = ActivityTopicField.NAME.lower()
group = GROUP.lower()
start = START.lower()
time = TIME.lower()
distance = DISTANCE.lower()


def search(args, system, db):
    '''
## search

    > ch2 search [-a|--advanced] QUERY [--show NAME ...] [--set NAME=VALUE]

This searches for activities.
Once a matching activity is found additional statistics can be displayed (--show)
and a single value modified (--set).

Simple searches (without --advanced) look for matches of all given words in the
name and notes fields for the activity.

The advanced syntax is similar to SQL, but element names are statistic names.
The name can include the activity group (start:bike) and SQL wildcards (%fitness%).
A name of the form "name:" matches any activity group;
"name" matches the activity group of the matched activity
(usually what is needed - the main exception is some statistics defined for group All).

For advanced searches string values must be quoted, negation and NULL values are not supported,
and comparison must be between a name and a value (not two names).

### Example

    > ch2 search --advanced 'name="Wrong Name"' --set 'name="Right Name"'

    '''
    query, show, set, advanced = args[QUERY], args[SHOW], args[SET], args[ADVANCED]
    if not show and not set: show = [ACTIVE_TIME, ACTIVE_DISTANCE]
    with db.session_context() as s:
        activities = unified_search(s, query, advanced=advanced)
        process_activities(s, activities, show, set)


def unified_search(s, query, advanced=True):
    if advanced:
        return constrained_activities(s, query)
    else:
        return simple_activity_search(s, query)


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
            name: {VALUE: value(StatisticJournal.for_source(s, topic_journal.id, ActivityTopicField.NAME,
                                                            ActivityTopic, activity_journal.activity_group)),
                   UNITS: None},
            group: {VALUE: activity_journal.activity_group.name, UNITS: None},
            start: {VALUE: time_to_local_time(activity_journal.start), UNITS: 'date'},
            time: format(StatisticJournal.for_source(s, activity_journal.id, ACTIVE_TIME,
                                                     ActivityCalculator, activity_journal.activity_group)),
            distance: format(StatisticJournal.for_source(s, activity_journal.id, ACTIVE_DISTANCE,
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
        log.debug(activity.id)
        print(f'{display(activity.get_named(s, START, owner=ActivityCalculator))}  {activity.activity_group.name}  '
              f'{display(activity.get_all_named(s, ActivityTopicField.NAME, owner=ActivityTopic))}')
        for qname in show:
            for result in activity.get_all_named(s, qname):
                print(f'  {result.statistic_name.name} = {result.formatted()}')
        if set:
            for result in activity.get_all_named(s, name):
                before = result.formatted()
                result.set(value)
                after = result.formatted()
            print(f'  {name}: {before!r} -> {after!r}')


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
        filter(StatisticName.name.in_([NOTES, ActivityTopicField.NAME]),
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
