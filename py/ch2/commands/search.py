from logging import getLogger

from .args import QUERY
from ..data import constrained_activities
from ..diary.model import DB, VALUE, UNITS
from ..lib import time_to_local_time
from ..sql import ActivityTopicJournal, FileHash, ActivityJournal, StatisticJournal, ActivityTopicField, ActivityTopic
from ..stats.calculate.activity import ActivityCalculator
from ..stats.names import TIME, START, ACTIVE_TIME, DISTANCE, ACTIVE_DISTANCE, GROUP

log = getLogger(__name__)


def search(args, system, db):
    '''
## search

    > ch2 search QUERY

This searches for activities.

The query syntax is similar to SQL, but element names are statistic names.
The name can include the activity group (start:bike) and SQL wildcards (%fitness).

Negation and NULL values are not supported.

This is still in development.
    '''
    query = args[QUERY]
    with db.session_context() as s:
        run_search(s, query)


def run_search(s, query):
    for aj in expanded_activities(s, query):
        print(aj)


def expanded_activities(s, query):
    return [expand_activity(s, activity) for activity in constrained_activities(s, query)]


def expand_activity(s, activity_journal):
    topic_journal = s.query(ActivityTopicJournal). \
        join(FileHash).join(ActivityJournal). \
        filter(ActivityJournal.id == activity_journal.id).one()
    NAME = ActivityTopicField.NAME

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
            NAME.lower(): {VALUE: value(StatisticJournal.for_source(s, topic_journal.id, NAME,
                                                                    ActivityTopic, activity_journal.activity_group)),
                           UNITS: None},
            GROUP.lower(): {VALUE: activity_journal.activity_group.name, UNITS: None},
            START.lower(): {VALUE: time_to_local_time(activity_journal.start), UNITS: 'date'},
            TIME.lower(): format(StatisticJournal.for_source(s, activity_journal.id, ACTIVE_TIME,
                                                             ActivityCalculator, activity_journal.activity_group)),
            DISTANCE.lower(): format(StatisticJournal.for_source(s, activity_journal.id, ACTIVE_DISTANCE,
                                                                 ActivityCalculator, activity_journal.activity_group))}
