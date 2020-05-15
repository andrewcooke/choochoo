
from ..commands.args import PATH, FORCE, parse_pairs, DEFINE, KARG, WORKER, KIT, BASE, FILENAME_KIT
from ..sql import PipelineType
from ..pipeline.pipeline import run_pipeline


def activities(args, sys, db):
    '''
## activities

    > ch2 activities [--kit ITEM [ITEM ...] --] [PATH [PATH ...]]

Read activities data from FIT files.

### Examples

    > ch2 activities -D kit=cotic ~/fit/2018-01-01.fit

will load the given file and associated the activity with the kit 'cotic'.

    > ch2 activities --kit

will load all unread files from the standard location
(constant Data.Dir, where they are stored by the upload command)
reading the kit from the file name (as encoded by the upload command).

Note: When using bash use `shopt -s globstar` to enable ** globbing.
    '''
    run_activity_pipelines(sys, db, args[BASE], paths=args[PATH], filename_kit=args[FILENAME_KIT],
                           force=args[FORCE], worker=args[WORKER] is not None, id=args[WORKER],
                           define=parse_pairs(args[DEFINE], convert=False, comma=True), **parse_pairs(args[KARG]))


def run_activity_pipelines(sys, db, base, paths=tuple(), filename_kit=True, force=False, worker=False, id=None,
                           define=None, **kargs):
    if define is None: define = {}
    run_pipeline(sys, db, base, PipelineType.READ_ACTIVITY, paths=paths, force=force, worker=worker, id=id,
                 define=define, filename_kit=filename_kit, **kargs)
