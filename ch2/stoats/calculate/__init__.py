
from ...squeal.tables.pipeline import Pipeline


def run_pipeline_after(log, db, type, after=None, force=False):
    with db.session_context() as s:
        for cls, args, kargs in Pipeline.all(log, s, type):
            log.info('Running %s (%s, %s)' % (cls, args, kargs))
            cls(log, db).run(*args, force=force, after=after, **kargs)


def run_pipeline_paths(log, db, type, paths, force=False):
    with db.session_context() as s:
        for cls, args, kargs in Pipeline.all(log, s, type):
            log.info('Running %s (%s, %s)' % (cls, args, kargs))
            cls(log, db).run(paths, *args, force=force, **kargs)
