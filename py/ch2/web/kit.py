from json import dumps
from logging import getLogger

from werkzeug import Response

from ..sql import KitGroup


log = getLogger(__name__)


class Kit:

    @staticmethod
    def read_statistics(request, s):
        data = [group.to_model(s, depth=3, statistics=True)
                for group in s.query(KitGroup).order_by(KitGroup.name).all()]
        print(data)
        return Response(dumps(data))
