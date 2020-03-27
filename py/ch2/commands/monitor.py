
from logging import getLogger

from ..commands.args import PATH, FORCE, FAST, WORKER, parse_pairs, KARG
from ..sql.tables.pipeline import PipelineType
from ..stats.pipeline import run_pipeline

log = getLogger(__name__)


def monitor(args, system, db):
    '''
## monitor

    > ch2 monitor PATH [PATH ...]

Read monitor data from FIT files.

Note: When using bash use `shopt -s globstar` to enable ** globbing.
    '''
    run_pipeline(system, db, PipelineType.MONITOR, paths=args[PATH], force=args[FORCE],
                 worker=args[WORKER] is not None, id=args[WORKER], **parse_pairs(args[KARG]))
