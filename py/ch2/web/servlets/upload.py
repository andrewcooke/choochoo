
from logging import getLogger

import psutil as ps

from ...commands.args import mm, WEB, UPLOAD, LOG, BASE, VERBOSITY
from ...commands.upload import upload_files_and_update, STREAM, NAME
from ...lib.log import Record
from ...lib.workers import command_root

log = getLogger(__name__)


class Upload:

    def __init__(self, sys, db, base):
        self._sys = sys
        self._db = db
        self._base = base

    def __call__(self, request, s):
        files = [{NAME: file.filename, STREAM: file.stream} for file in request.files.getlist('files')]
        items = request.form.getlist('kit')
        # we do this in two stages
        # first, immediate saving of files while web browser waiting for response
        upload_files_and_update(Record(log), self._sys, self._db, self._base, files=files, items=items, fast=True)
        # second, start rest of ingest process in background
        # tui to avoid stdout appearing on web service output
        cmd = f'{command_root()} {mm(VERBOSITY)} 0 {mm(BASE)} {self._base} {mm(LOG)} {WEB}-{UPLOAD}.log {UPLOAD}'
        log.info(f'Starting {cmd}')
        ps.Popen(args=cmd, shell=True)
        # wait so that the progress has time to kick in
        self._sys.wait_for_progress(UPLOAD)
