from logging import getLogger

from werkzeug import Response

log = getLogger(__name__)


class Upload:

    def __call__(self, request, s):
        data = request.json
        log.debug(data)
        return Response()
