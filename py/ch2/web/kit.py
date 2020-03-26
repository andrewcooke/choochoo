from logging import getLogger

from werkzeug import Response

from .json import JsonResponse
from ..commands.kit import finish, change, start
from ..lib import local_date_to_time, now
from ..sql import KitGroup, KitComponent, KitItem
from ..sql.tables.kit import MODELS, ITEMS, ITEM, COMPONENT, MODEL, INDIVIDUAL, POPULATION, GROUP

log = getLogger(__name__)


class Kit:
    '''
    These are / should be very thin wrappers around the equivalent kit commands.
    We don't try to implement all commands, just the basics.
    If necessary, the user can drop down to the command line.
    '''

    @staticmethod
    def _delete_item_models(groups):
        for group in groups:
            for item in group[ITEMS]:
                del item[MODELS]
        return groups

    @staticmethod
    def read_snapshot(request, s, date):
        groups = [group.to_model(s, depth=3, statistics=INDIVIDUAL, time=local_date_to_time(date))
                  for group in s.query(KitGroup).order_by(KitGroup.name).all()]
        return JsonResponse(groups)

    @staticmethod
    def read_edit(request, s):
        data = [group.to_model(s, depth=3, statistics=None, time=now(), own_models=False)
                for group in s.query(KitGroup).order_by(KitGroup.name).all()]
        return JsonResponse(data)

    @staticmethod
    def read_statistics(request, s):
        components = [component.to_model(s, depth=3, statistics=POPULATION)
                      for component in s.query(KitComponent).order_by(KitComponent.name).all()]
        return JsonResponse(components)

    @staticmethod
    def read_items(request, s):
        items = [item.to_model(s, depth=0)
                 for item in s.query(KitItem).order_by(KitItem.name).all()]
        return JsonResponse(items)

    @staticmethod
    def write_retire_item(request, s):
        data = request.json
        log.debug(data)
        finish(s, data[ITEM], None, True)
        return Response()

    @staticmethod
    def write_replace_model(request, s):
        data = request.json
        log.debug(data)
        change(s, data[ITEM], data[COMPONENT], data[MODEL], None, False, False)
        return Response()

    @staticmethod
    def write_add_component(request, s):
        data = request.json
        log.debug(data)
        change(s, data[ITEM], data[COMPONENT], data[MODEL], None, True, False)
        return Response()

    @staticmethod
    def write_add_group(request, s):
        data = request.json
        log.debug(data)
        start(s, data[GROUP], data[ITEM], None, True)
        return Response()
