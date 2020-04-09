from json import dumps
from logging import getLogger

from werkzeug import Response


log = getLogger(__name__)


class JsonResponse(Response):

    default_mimetype = 'application/json'

    def __init__(self, content, **kargs):
        super().__init__(dumps(content), **kargs)
