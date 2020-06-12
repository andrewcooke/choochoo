from collections import defaultdict
from logging import getLogger

import psutil as ps

from ...commands.args import mm, WEB, READ, LOG, BASE, VERBOSITY, FORCE
from ...commands.read import upload_files_and_update, STREAM, NAME
from ...lib.log import Record
from ...lib.utils import parse_bool
from ...lib.workers import command_root

log = getLogger(__name__)


class Upload:

    def __init__(self, data):
        self.__data = data

    def __call__(self, request, s):
        files = [{NAME: file.filename, STREAM: file.stream} for file in request.files.getlist('files')]
        items = request.form.getlist('kit')
        force = parse_bool(request.form.get('force'))
        # we do this in two stages
        # first, immediate saving of files while web browser waiting for response
        upload_files_and_update(Record(log), self.__data, files=files, items=items, flags=defaultdict(lambda: False))
        # second, start rest of ingest process in background
        # tui to avoid stdout appearing on web service output
        cmd = f'{command_root()} {mm(VERBOSITY)} 0 {mm(BASE)} {self.__data.base} {mm(LOG)} {WEB}-{READ}.log {READ}'
        if force: cmd += f' {mm(FORCE)}'
        log.info(f'Starting {cmd}')
        ps.Popen(args=cmd, shell=True)
        # wait so that the progress has time to kick in
        self.__data.sys.wait_for_progress(READ)
