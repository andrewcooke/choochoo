
from ..squeal.tables.statistic import StatisticPipeline


def run_statistics(log, db, force=False, after=None):
    with db.session_context() as s:
        data = [(pipeline.cls, pipeline.args, pipeline.kargs)
                   for pipeline in s.query(StatisticPipeline).order_by(StatisticPipeline.sort).all()]
    for cls, args, kargs in data:
        log.info('Running %s (%s, %s)' % (cls, args, kargs))
        cls(log, db).run(*args, force=force, after=after, **kargs)
