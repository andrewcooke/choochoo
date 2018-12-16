import datetime as dt
from abc import abstractmethod

from ch2.lib.date import local_date_to_time
from ch2.squeal import ActivityGroup, ActivityJournal

from .. import BasePipeline
from ...lib.date import to_date
from ...squeal.tables.pipeline import Pipeline


def build_pipeline(log, session, type, factory, date, schedule=None):
    '''
    schedule only sent for summary views.
    '''
    date = to_date(date)   # why is this needed?
    for cls, args, kargs in Pipeline.all(log, session, type):
        log.info('Building %s (%s, %s)' % (cls, args, kargs))
        yield from cls(log, *args, **kargs).build(session, factory, date, schedule=schedule)


class Displayer(BasePipeline):

    def build(self, s, f, date, schedule=None):
        if schedule:
            yield from self._build_schedule(s, f, date, schedule=schedule)
        else:
            yield from self._build_date(s, f, date)

    @abstractmethod
    def _build_schedule(self, s, f, date, schedule=None):
        raise NotImplementedError()

    @abstractmethod
    def _build_date(self, s, f, date):
        raise NotImplementedError()


class JournalDiary(Displayer):

    def _build_date(self, s, f, date):
        start = local_date_to_time(date)
        finish = start + dt.timedelta(days=1)
        for activity_group in s.query(ActivityGroup).order_by(ActivityGroup.sort).all():
            for journal in s.query(ActivityJournal). \
                    filter(ActivityJournal.finish >= start,
                           ActivityJournal.start < finish,
                           ActivityJournal.activity_group == activity_group). \
                    order_by(ActivityJournal.start).all():
                yield from self._journal_date(s, journal, date)

    @abstractmethod
    def _journal_date(self, s, ajournal, date):
        raise NotImplementedError()
