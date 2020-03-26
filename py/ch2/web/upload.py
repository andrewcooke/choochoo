from logging import getLogger

from werkzeug import Response

log = getLogger(__name__)


class Upload:

    def __call__(self, request, s):
        log.debug(request.form)
        log.debug(request.files)
        return Response()
