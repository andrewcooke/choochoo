from logging import getLogger

from sqlalchemy import func

from ..json import JsonResponse
from ...commands.search import expanded_activities
from ...sql import StatisticName, ActivityGroup, ActivityJournal, StatisticJournal, Source
from ...sql.tables.source import SourceType


log = getLogger(__name__)

NAME = 'name'
DESCRIPTION = 'description'
GROUPS = 'groups'
UNITS = 'units'


class Search:

    @staticmethod
    def query_activity(request, s, query):
        return JsonResponse(expanded_activities(s, query))

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
