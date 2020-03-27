from logging import getLogger

from werkzeug import Response

from ..commands.upload import upload_data, STREAM

log = getLogger(__name__)


class Upload:

    def __init__(self, system, db):
        self._system = system
        self._db = db

    def __call__(self, request, s):
        files = {file.filename: {STREAM: file.stream} for file in request.files.getlist('files')}
        items = request.form.getlist('kit')
        upload_data(self._system, self._db, files=files, items=items)
        return Response()
