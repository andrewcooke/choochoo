
from ...squeal.tables.pipeline import Pipeline


def build_pipeline(log, session, type, factory, date):
    for cls, args, kargs in Pipeline.all(log, session, type):
        log.info('Building %s (%s, %s)' % (cls, args, kargs))
        yield from cls(log).build(session, factory, date, *args, **kargs)
