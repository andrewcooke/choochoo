
from ..command.args import PATH, FORCE, FAST
from ..squeal.tables.config import ActivityPipeline
from ..stoats.calculate import run_statistics


def activities(args, log, db):
    '''
# activities

    ch2 activities PATH [PATH ...]

Read activities from fit files.
    '''
    force, fast = args[FORCE], args[FAST]
    paths = args[PATH]
    run_activities(log, db, paths, force=force)
    if not fast:
        run_statistics(log, db, force=force)


def run_activities(log, db, paths, force=False):
    with db.session_context() as s:
        for cls, args, kargs in ((pipeline.cls, pipeline.args, pipeline.kargs)
                                 for pipeline in s.query(ActivityPipeline).order_by(ActivityPipeline.sort).all()):
            log.info('Running %s (%s, %s)' % (cls, args, kargs))
            cls(log, db).run(paths, *args, force=force, **kargs)


