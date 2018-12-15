
from ..command.args import PATH, FORCE, FAST
from ..squeal.tables.pipeline import PipelineType
from ..stoats.calculate import run_pipeline_after, run_pipeline_paths


def activities(args, log, db):
    '''
## activities

    > ch2 activities PATH [PATH ...]

Read activities data from FIT files.

Note: When using bash use `shopt -s globstar` to enable ** globbing.
    '''
    force, fast, paths = args[FORCE], args[FAST], args[PATH]
    run_pipeline_paths(log, db, PipelineType.ACTIVITY, paths, force=force)
    if not fast:
        run_pipeline_after(log, db, PipelineType.STATISTIC, force=force)
