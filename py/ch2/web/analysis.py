from logging import getLogger

from .json import JsonResponse
from ..lib import time_to_local_time
from ..stats.display.activity import latest_activity, activities_start, activities_finish, \
    activities_by_group
from ..stats.display.nearby import constraints

log = getLogger(__name__)


class Analysis:

    @staticmethod
    def read_parameters(request, s):
        # odds and sods used to set menus in jupyter URLs
        latest = latest_activity(s)
        return {'activities_start': activities_start(s),
                'activities_finish': activities_finish(s),
                'activities_by_group': activities_by_group(s),
                'latest_activity_group': latest.activity_group.name if latest else None,
                'latest_activity_time': time_to_local_time(latest.start) if latest else None,
                'nearby_constraints': list(constraints(s))}
