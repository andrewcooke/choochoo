
from logging import getLogger

from ...pipeline.display.activity.utils import latest_activity, activity_times_by_group

log = getLogger(__name__)


class Analysis:

    @staticmethod
    def read_parameters(request, s):
        # odds and sods used to set menus in jupyter URLs
        latest = latest_activity(s)
        times_by_group = activity_times_by_group(s)
        all_activity_times = sorted(sum(times_by_group.values(), []), reverse=True)
        return {'all_activity_times': all_activity_times,
                'activity_times_by_group': times_by_group,
                'latest_activity_group': latest.activity_group.name if latest else None}
