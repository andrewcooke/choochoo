
import datetime as dt
from abc import abstractmethod

from ch2.stoats.pipeline import BasePipeline
from ...lib.date import local_date_to_time
from ...lib.date import to_date
from ...squeal import ActivityGroup, ActivityJournal
from ...squeal.tables.pipeline import Pipeline, PipelineType


def display_pipeline(log, session, factory, date, diary, schedule=None):
    '''
    schedule only sent for summary views.
    '''
    date = to_date(date)   # why is this needed?
    for cls, args, kargs in Pipeline.all(log, session, PipelineType.DIARY):
        log.info('Building %s (%s, %s)' % (cls, args, kargs))
        yield from cls(log, *args, diary=diary, **kargs).display(session, factory, date, schedule=schedule)


class Displayer(BasePipeline):

    def _on_init(self, *args, diary=None, **kargs):
        self._diary = diary
        super()._on_init(*args, **kargs)

    def display(self, s, f, date, schedule=None):
        if schedule:
            yield from self._display_schedule(s, f, date, schedule=schedule)
        else:
            yield from self._display_date(s, f, date)

    @abstractmethod
    def _display_schedule(self, s, f, date, schedule=None):
        raise NotImplementedError()

    @abstractmethod
    def _display_date(self, s, f, date):
        raise NotImplementedError()


class JournalDiary(Displayer):

    def _display_date(self, s, f, date):
        start = local_date_to_time(date)
        finish = start + dt.timedelta(days=1)
        for activity_group in s.query(ActivityGroup).order_by(ActivityGroup.sort).all():
            for journal in s.query(ActivityJournal). \
                    filter(ActivityJournal.finish >= start,
                           ActivityJournal.start < finish,
                           ActivityJournal.activity_group == activity_group). \
                    order_by(ActivityJournal.start).all():
                yield from self._journal_date(s, f, journal, date)

    @abstractmethod
    def _journal_date(self, s, f, ajournal, date):
        raise NotImplementedError()
