from logging import getLogger

from .. import DEV
from ..commands.args import LOG
from ..common.args import mm
from ..common.global_ import global_dev
from ..common.names import VERBOSITY, BASE, URI
from ..lib.workers import command_root

log = getLogger(__name__)


def run(config, cmd, owner, log_name):
    full_cmd = f'{command_root()} {mm(VERBOSITY)} 0 {mm(BASE)} {config.args[BASE]} ' \
               f'{mm(URI)} {config.args._format(URI)} {mm(LOG)} {log_name}'
    if global_dev(): full_cmd += f' {mm(DEV)}'
    full_cmd += f' {cmd}'
    log.info(f'Starting {full_cmd}')
    return config.run_process(owner, full_cmd, log_name)


def run_and_wait(config, cmd, owner, log_name):
    popen = run(config, cmd, owner, log_name)
    popen.wait()
    config.delete_process(owner, popen.pid)
    return popen.returncode
