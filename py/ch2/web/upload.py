
import psutil as ps
from logging import getLogger

from werkzeug import Response

from ..commands.args import mm, WEB, UPLOAD, TUI, LOG
from ..commands.upload import upload_files_and_update, STREAM, NAME
from ..lib.workers import command_root

log = getLogger(__name__)


class Upload:

    def __init__(self, sys, db):
        self._sys = sys
        self._db = db

    def __call__(self, request, s):
        files = [{NAME: file.filename, STREAM: file.stream} for file in request.files.getlist('files')]
        items = request.form.getlist('kit')
        # we do this in two stages
        # first, immediate saving of files while web browser waiting for response
        upload_files_and_update(self._sys, self._db, files=files, items=items, fast=True)
        # second, start rest of ingest process in background
        # tui to avoid stdout appearing on web service output
        cmd = f'{command_root()} -v5 {mm(TUI)} {mm(LOG)} {WEB}-{UPLOAD}.log {UPLOAD}'
        log.info(f'Starting {cmd}')
        ps.Popen(args=cmd, shell=True)
        # wait so that the progress has time to kick in
        self._sys.wait_for_progress(UPLOAD)
        return Response()
