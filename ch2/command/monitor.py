
from ..command.args import PATH, FORCE, FAST
from ..squeal.tables.pipeline import PipelineType
from ..stoats.calculate import run_pipeline_paths, run_pipeline_after


def monitor(args, log, db):
    '''
## monitor

    > ch2 monitor PATH [PATH ...]

Read monitor data from FIT files.

Note: When using bash use `shopt -s globstar` to enable ** globbing.
    '''
    force, fast, paths = args[FORCE], args[FAST], args[PATH]
    run_pipeline_paths(log, db, PipelineType.MONITOR, paths, force=force)
    if not fast:
        run_pipeline_after(log, db, PipelineType.STATISTIC, force=force)
