from logging import getLogger

from .args import QUERY, SHOW, SET
from ..data import constrained_activities
from ..diary.model import DB, VALUE, UNITS
from ..lib import time_to_local_time
from ..sql import ActivityTopicJournal, FileHash, ActivityJournal, StatisticJournal, ActivityTopicField, ActivityTopic
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

    > ch2 search QUERY [--show NAME ...] [--set NAME=VALUE]

This searches for activities.

The query syntax is similar to SQL, but element names are statistic names.
The name can include the activity group (start:bike) and SQL wildcards (%fitness%).

Negation and NULL values are not supported.

This is still in development.
    '''
    query, show, set = args[QUERY], args[SHOW], args[SET]
    if not show: show = [ACTIVE_TIME, ACTIVE_DISTANCE]
    with db.session_context() as s:
        activities = constrained_activities(s, query)
        process_activities(s, activities, show, set)


def expanded_activities(s, query):
    return [expand_activity(s, activity) for activity in constrained_activities(s, query)]


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


def process_activities(s, activities, show, set):
    if set:
        name, value = [x.strip() for x in set.split('=', 1)]
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

