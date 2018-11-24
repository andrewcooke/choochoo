
from abc import abstractmethod

from ...lib.date import to_date
from ...squeal.tables.pipeline import Pipeline


def build_pipeline(log, session, type, factory, date, schedule=None):
    date = to_date(date)   # why is this needed?
    for cls, args, kargs in Pipeline.all(log, session, type):
        log.info('Building %s (%s, %s)' % (cls, args, kargs))
        yield from cls(log).build(session, factory, date, *args, schedule=schedule, **kargs)


class Displayer:

    def __init__(self, log):
        self._log = log

    def build(self, s, f, date, *args, schedule=None, **kargs):
        if schedule:
            yield from self._build_schedule(s, f, date, *args, schedule=schedule, **kargs)
        else:
            yield from self._build_date(s, f, date, *args, **kargs)

    @abstractmethod
    def _build_schedule(self, s, f, date, *args, schedule=None, **kargs):
        raise NotImplementedError()

    @abstractmethod
    def _build_date(self, s, f, date, *args, **kargs):
        raise NotImplementedError()
