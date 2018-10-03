
from ..squeal.tables.statistic import StatisticPipeline


def run_statistics(log, db, force=False, date=None):
    with db.session_context() as s:
        classes = [pipeline.cls
                   for pipeline in s.query(StatisticPipeline).order_by(StatisticPipeline.sort).all()]
    for cls in classes:
        log.info('Running %s' % cls)
        cls(log, db).run(force=force, date=date)
