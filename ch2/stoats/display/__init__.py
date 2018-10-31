
import datetime as dt

from ...lib.date import local_date_to_time
from ...squeal.tables.pipeline import Pipeline
from ...squeal.tables.source import Source
from ...squeal.tables.statistic import StatisticJournal, StatisticName


def build_pipeline(log, session, type, factory, date, schedule=None):
    for cls, args, kargs in Pipeline.all(log, session, type):
        log.info('Building %s (%s, %s)' % (cls, args, kargs))
        yield from cls(log).build(session, factory, date, *args, schedule=schedule, **kargs)


class Displayer:

    def __init__(self, log):
        self._log = log

    def _journal_at_date(self, s, date, name, owner, constraint):
        start = local_date_to_time(date)
        finish = start + dt.timedelta(days=1)
        return s.query(StatisticJournal).join(StatisticName, Source). \
            filter(StatisticName.name == name,
                   Source.time >= start,
                   Source.time < finish,
                   StatisticName.owner == owner,
                   StatisticName.constraint == constraint).one_or_none()

    def _journal_at_time(self, s, time, name, owner, constraint):
        return s.query(StatisticJournal).join(StatisticName, Source). \
            filter(StatisticName.name == name,
                   Source.time == time,
                   StatisticName.owner == owner,
                   StatisticName.constraint == constraint).one_or_none()
