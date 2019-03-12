
from ..commands.args import PATH, FORCE, FAST, CONSTANTS
from ..squeal import PipelineType
from ..stoats.pipeline import run_pipeline


def activities(args, log, db):
    '''
## activities

    > ch2 activities PATH [PATH ...]

Read activities data from FIT files.

### Examples

    > ch2 activities -D 'Bike=Cotic Soul' ~/fit/2018-01-01.fit

will load the give file and create an entry for the `Bike` statistic with value `Cotic Soul`
(this particular variable is used to identify bike-specific parameters for power calculation,
but arbitrary names and values can be used).

Note: When using bash use `shopt -s globstar` to enable ** globbing.
    '''
    constants = parse_constants(args[CONSTANTS]) if args[CONSTANTS] else {}
    force, fast, paths = args[FORCE], args[FAST], args[PATH]
    run_pipeline(log, db, PipelineType.ACTIVITY, paths=paths, force=force, constants=constants)
    if not fast:
        # don't force this - it auto-detects need
        run_pipeline(log, db, PipelineType.STATISTIC)


def parse_constants(clist):
    # simple name, value pairs.  owner and constraint supplied by command.
    constants = {}
    for constant in clist:
        name, value = constant.split('=', 1)
        constants[name] = value
    return constants
