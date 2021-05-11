from logging import getLogger

from sqlalchemy import distinct

from ..json import JsonResponse
from ...data import constrained_sources
from ...data.constraint import activity_conversion
from ...diary.model import VALUE, UNITS, DB
from ...lib import time_to_local_time
from ...lib.utils import parse_bool
from ...names import N
from ...pipeline.calculate import ActivityCalculator
from ...sql import StatisticName, StatisticJournal, Source, ActivityTopic
from ...sql.tables.source import SourceType

log = getLogger(__name__)

NAME = 'name'
DESCRIPTION = 'description'
GROUPS = 'groups'

RESULTS = 'results'
ERROR = 'error'


class Search:

    @staticmethod
    def query_activity(request, s, query):
        try:
            advanced = parse_bool(request.args.get('advanced', 'false'), default=None)
            log.info(f'{"advanced " if advanced else ""}query: {query}')
            return JsonResponse({RESULTS: search(s, query, advanced)})
        except Exception as e:
            log.warning(e)
            return JsonResponse({ERROR: str(e)})

    @staticmethod
    def read_activity_terms(request, s):

        def format(row):
            name, description, units = row
            return {NAME: name, DESCRIPTION: description, UNITS: units}

        used = s.query(distinct(StatisticJournal.statistic_name_id)). \
            join(Source, Source.id == StatisticJournal.source_id). \
            filter(Source.type.in_([SourceType.ACTIVITY_TOPIC, SourceType.ACTIVITY]))
        q = s.query(StatisticName.name, StatisticName.description, StatisticName.units). \
            filter(StatisticName.id.in_(used))
        log.debug(q)
        return JsonResponse([format(row) for row in q.all()])


def search(s, query, advanced):
    if advanced:
        activities = constrained_sources(s, query, conversion=activity_conversion)
    else:
        query = ' and '.join([f'(ActivityTopic.name = "{word}" or ActivityTopic.notes = "{word}")'
                              for word in query.split()])
        activities = constrained_sources(s, query, activity_conversion)
    log.debug(f'Have {len(activities)} activities')
    return [expand_activity(s, activity) for activity in sorted(activities, key=lambda x: x.start)]


def expand_activity(s, activity_journal):

    topic_journal = activity_journal.get_activity_topic_journal(s)

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
                                                              ActivityTopic, topic_journal.activity_group)),
                     UNITS: None},
            'group': {VALUE: activity_journal.activity_group.name, UNITS: None},
            'start': {VALUE: time_to_local_time(activity_journal.start), UNITS: 'date'},
            'time': format(StatisticJournal.for_source(s, activity_journal.id, N.ACTIVE_TIME,
                                                       ActivityCalculator, activity_journal.activity_group)),
            'distance': format(StatisticJournal.for_source(s, activity_journal.id, N.ACTIVE_DISTANCE,
                                                           ActivityCalculator, activity_journal.activity_group))}
