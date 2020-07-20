from logging import getLogger

import psutil as ps

from ...commands.args import WEB, READ, LOG, VERBOSITY, FORCE, DEV, URI
from ...common.args import mm
from ...common.names import BASE
from ...commands.upload import STREAM, NAME, upload_files
from ...common.global_ import global_dev
from ...lib.log import Record
from ...lib.utils import parse_bool
from ...lib.workers import command_root

log = getLogger(__name__)


class Upload:

    def __init__(self, config):
        self.__config = config

    def __call__(self, request, s):
        files = [{NAME: file.filename, STREAM: file.stream} for file in request.files.getlist('files')]
        items = request.form.getlist('kit')
        force = parse_bool(request.form.get('force'))
        # we do this in two stages
        # first, immediate saving of files while web browser waiting for response
        upload_files(Record(log), self.__config, files=files, nfiles=len(files), items=items)
        # second, start rest of ingest process in background
        cmd = f'{command_root()} {mm(VERBOSITY)} 0 {mm(BASE)} {self.__config.args[BASE]} {mm(LOG)} {WEB}-{READ}.log ' \
              f'{mm(URI)} {self.__config.args._format(URI)}'
        if global_dev(): cmd += f' {mm(DEV)}'
        cmd += f' {READ}'
        if force: cmd += f' {mm(FORCE)}'
        log.info(f'Starting {cmd}')
        ps.Popen(args=cmd, shell=True)
        # wait so that the progress has time to kick in
        self.__config.wait_for_progress(READ)
