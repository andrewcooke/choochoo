from logging import getLogger

from werkzeug import Response

from ..commands.upload import upload_files_and_update, STREAM, NAME

log = getLogger(__name__)


class Upload:

    def __init__(self, system, db):
        self._system = system
        self._db = db

    def __call__(self, request, s):
        files = [{NAME: file.filename, STREAM: file.stream} for file in request.files.getlist('files')]
        items = request.form.getlist('kit')
        upload_files_and_update(self._system, self._db, files=files, items=items)
        return Response()
