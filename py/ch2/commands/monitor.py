
from logging import getLogger

from ..commands.args import PATH, FORCE, FAST, WORKER, parse_pairs, KARG, BASE
from ..sql.tables.pipeline import PipelineType
from ..pipeline.pipeline import run_pipeline

log = getLogger(__name__)


def monitor(args, sys, db):
    '''
## monitor

    > ch2 monitor PATH [PATH ...]

Read monitor data from FIT files.

Note: When using bash use `shopt -s globstar` to enable ** globbing.
    '''
    run_monitor_pipelines(sys, db, args[BASE], paths=args[PATH], force=args[FORCE],
                          worker=args[WORKER] is not None, id=args[WORKER], **parse_pairs(args[KARG]))


def run_monitor_pipelines(sys, db, base, paths=None, force=False, worker=False, id=None, **kargs):
    if paths is None: paths = []
    run_pipeline(sys, db, base, PipelineType.MONITOR, paths=paths, force=force, worker=worker, id=id, **kargs)
