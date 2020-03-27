
from ..commands.args import PATH, FORCE, FAST, parse_pairs, DEFINE, KARG, WORKER
from ..sql import PipelineType
from ..stats.pipeline import run_pipeline


def activities(args, system, db):
    '''
## activities

    > ch2 activities [--kit ITEM [ITEM ...] --] PATH [PATH ...]

Read activities data from FIT files.

### Examples

    > ch2 activities -D kit=cotic ~/fit/2018-01-01.fit

will load the given file and associated the activity with the kit 'cotic'.

Note: When using bash use `shopt -s globstar` to enable ** globbing.
    '''
    run_pipeline(system, db, PipelineType.ACTIVITY, paths=args[PATH], force=args[FORCE],
                 worker=args[WORKER] is not None, id=args[WORKER],
                 define=parse_pairs(args[DEFINE], convert=False), **parse_pairs(args[KARG]))
