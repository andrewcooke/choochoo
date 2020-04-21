from logging import getLogger

from .args import QUERY, SHOW, SET
from ..data import constrained_activities
from ..diary.model import DB, VALUE, UNITS
from ..lib import time_to_local_time
from ..sql import ActivityTopicJournal, FileHash, ActivityJournal, StatisticJournal, ActivityTopicField, ActivityTopic, \
    StatisticName, ActivityGroup
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
The name can include the activity group (start:bike) and SQL wildcards (%fitness).

Negation and NULL values are not supported.

This is still in development.
    '''
    query, show, set = args[QUERY], args[SHOW], args[SET]
    if not show: show = [ACTIVE_TIME, ACTIVE_DISTANCE]
    with db.session_context() as s:
        activities = constrained_activities(s, query)
        show_activities(s, activities, show)


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


def show_activities(s, activities, show):
    for activity in activities:
        expanded = expand_activity(s, activity)
        print(f'{expanded[start][VALUE]}  {expanded[name][VALUE]}:{expanded[group][VALUE]}')
        for full_name in show:
            if ':' in full_name:
                sname, agroup = full_name.split(':')
                activity_group = ActivityGroup.from_name(s, agroup)
                query = s.query(StatisticJournal). \
                    join(StatisticName). \
                    filter(StatisticName.constraint == activity_group,
                           StatisticName.name == sname,
                           StatisticJournal.source == activity)
            else:
                query = s.query(StatisticJournal). \
                    join(StatisticName). \
                    filter(StatisticName.name == full_name,
                           StatisticJournal.source == activity)
            for journal in query.all():
                print(f'  {journal.statistic_name.name}:{journal.statistic_name.constraint} = {journal.value}')

