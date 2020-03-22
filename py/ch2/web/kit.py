from json import dumps
from logging import getLogger

from .json import JsonResponse
from ..lib import local_date_to_time
from ..sql import KitGroup

log = getLogger(__name__)


class Kit:

    @staticmethod
    def read_snapshot(request, s, date):
        data = [group.to_model(s, depth=3, statistics=True, time=local_date_to_time(date))
                for group in s.query(KitGroup).order_by(KitGroup.name).all()]
        return JsonResponse(data)

    @staticmethod
    def read_structure(request, s):
        data = [group.to_model(s, depth=3, statistics=False)
                for group in s.query(KitGroup).order_by(KitGroup.name).all()]
        return JsonResponse(data)
