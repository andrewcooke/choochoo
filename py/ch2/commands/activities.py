
from ..commands.args import PATH, FORCE, FAST, parse_pairs, CONSTANT, KARG, WORKER
from ..sql import PipelineType
from ..stats.pipeline import run_pipeline


def activities(args, system, db):
    '''
## activities

    > ch2 activities PATH [PATH ...]

Read activities data from FIT files.

### Examples

    > ch2 activities -D kit=cotic ~/fit/2018-01-01.fit

will load the give file and create an entry for the `Bike` statistic with value `Cotic Soul`
(this particular variable is used to identify bike-specific parameters for power calculation,
but arbitrary names and values can be used).

Note: When using bash use `shopt -s globstar` to enable ** globbing.
    '''
    run_pipeline(system, db, PipelineType.ACTIVITY, paths=args[PATH], force=args[FORCE],
                 worker=args[WORKER] is not None, id=args[WORKER],
                 constants=args[CONSTANT], **parse_pairs(args[KARG]))
    if not args[FAST] and args[WORKER] is None:
        # don't force this - it auto-detects need
        run_pipeline(system, db, PipelineType.STATISTIC, **parse_pairs(args[KARG]))
