from json import dumps

from werkzeug import Response


class JsonResponse(Response):

    default_mimetype = 'application/json'

    def __init__(self, content, **kargs):
        super().__init__(dumps(content), **kargs)
