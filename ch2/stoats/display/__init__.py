
from ...squeal.tables.pipeline import Pipeline


def build_pipeline(log, session, type, factory, date):
    for cls, args, kargs in ((pipeline.cls, pipeline.args, pipeline.kargs)
                             for pipeline in session.query(Pipeline).
                                     filter(Pipeline.type == type).
                                     order_by(Pipeline.sort).all()):
        log.info('Building %s (%s, %s)' % (cls, args, kargs))
        yield from cls(log).build(session, factory, date, *args, **kargs)
