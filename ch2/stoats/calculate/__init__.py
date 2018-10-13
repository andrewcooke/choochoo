
from ...squeal.tables.config import StatisticPipeline


def run_statistics(log, db, force=False, after=None):
    with db.session_context() as s:
        for cls, args, kargs in ((pipeline.cls, pipeline.args, pipeline.kargs)
                                 for pipeline in s.query(StatisticPipeline).order_by(StatisticPipeline.sort).all()):
            log.info('Running %s (%s, %s)' % (cls, args, kargs))
            cls(log, db).run(*args, force=force, after=after, **kargs)
