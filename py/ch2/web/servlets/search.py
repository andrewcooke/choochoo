from logging import getLogger

from sqlalchemy import func

from ..json import JsonResponse
from ...commands.search import expand_activities, unified_search
from ...lib.utils import parse_bool
from ...sql import StatisticName, ActivityGroup, StatisticJournal, Source
from ...sql.tables.source import SourceType

log = getLogger(__name__)

NAME = 'name'
DESCRIPTION = 'description'
GROUPS = 'groups'
UNITS = 'units'

RESULTS = 'results'
ERROR = 'error'


class Search:

    @staticmethod
    def query_activity(request, s, query):
        try:
            advanced = parse_bool(request.args.get('advanced', 'false'), default=None)
            return JsonResponse({RESULTS: expand_activities(s, unified_search(s, query, advanced=advanced))})
        except Exception as e:
            return JsonResponse({ERROR: str(e)})

    @staticmethod
    def read_activity_terms(request, s):

        def format(row):
            name, description,units,  groups = row
            groups = ', '.join(sorted(groups.split(',')))
            return {NAME: name, DESCRIPTION: description, GROUPS: groups, UNITS: units}

        q = s.query(StatisticName.name, StatisticName.description, StatisticName.units,
                    func.group_concat(ActivityGroup.name.distinct())). \
            join(ActivityGroup). \
            join(StatisticJournal). \
            join(Source, Source.id == StatisticJournal.source_id). \
            filter(Source.type.in_([SourceType.ACTIVITY_TOPIC, SourceType.ACTIVITY])). \
            group_by(StatisticName.name). \
            order_by(StatisticName.name)
        log.debug(q)
        return JsonResponse([format(row) for row in q.all()])
