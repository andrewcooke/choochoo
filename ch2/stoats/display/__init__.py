
from ...squeal.tables.pipeline import Pipeline


def build_pipeline(log, session, type, factory, date, schedule=None):
    for cls, args, kargs in Pipeline.all(log, session, type):
        log.info('Building %s (%s, %s)' % (cls, args, kargs))
        yield from cls(log).build(session, factory, date, *args, schedule=schedule, **kargs)


class Displayer:

    def __init__(self, log):
        self._log = log

