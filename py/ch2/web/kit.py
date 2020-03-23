from json import dumps
from logging import getLogger

from werkzeug import Response

from .json import JsonResponse
from ..lib import local_date_to_time, now
from ..sql import KitGroup
from ..sql.tables.kit import MODELS, ITEMS

log = getLogger(__name__)


class Kit:

    @staticmethod
    def _delete_item_models(groups):
        for group in groups:
            for item in group[ITEMS]:
                del item[MODELS]
        return groups

    @staticmethod
    def read_statistics(request, s, date):
        groups = [group.to_model(s, depth=3, statistics=True, time=local_date_to_time(date))
                  for group in s.query(KitGroup).order_by(KitGroup.name).all()]
        for group in groups:
            for item in group[ITEMS]:
                del item[MODELS]
        return JsonResponse(groups)

    @staticmethod
    def read_edit(request, s):
        data = [group.to_model(s, depth=3, statistics=False, time=now(), own_models=False)
                for group in s.query(KitGroup).order_by(KitGroup.name).all()]
        return JsonResponse(data)

    def write_retire_item(self, request, s):
        data = request.json
        log.info(data)
        return Response()

    def write_replace_model(self, request, s):
        data = request.json
        log.info(data)
        return Response()

    def write_add_component(self, request, s):
        data = request.json
        log.info(data)
        return Response()

