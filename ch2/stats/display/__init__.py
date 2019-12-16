
import datetime as dt
from abc import abstractmethod
from logging import getLogger

from ...lib.date import local_date_to_time
from ...lib.date import to_date
from ...sql import ActivityGroup, ActivityJournal
from ...sql.tables.pipeline import Pipeline, PipelineType
from ...stats.pipeline import BasePipeline

log = getLogger(__name__)


def display_pipeline(session, factory, date, diary, schedule=None):
    '''
    schedule only sent for summary views.
    '''
    date = to_date(date)   # why is this needed?
    for pipeline in Pipeline.all(session, PipelineType.DIARY):
        log.info(f'Building {pipeline.cls} ({pipeline.args}, {pipeline.kargs})')
        yield from pipeline.cls(*pipeline.args, diary=diary, **pipeline.kargs). \
            display(session, factory, date, schedule=schedule)


def read_pipeline(session, date, schedule=None):
    '''
    schedule only sent for summary views.
    '''
    date = to_date(date)   # why is this needed?
    for pipeline in Pipeline.all(session, PipelineType.DIARY):
        log.info(f'Building {pipeline.cls} ({pipeline.args}, {pipeline.kargs})')
        instance = pipeline.cls(*pipeline.args, **pipeline.kargs)
        if isinstance(instance, Reader):
            yield from instance.read(session, date, schedule=schedule)


class Displayer(BasePipeline):

    def __init__(self, *args, diary=None, **kargs):
        self._diary = diary
        super().__init__(*args, **kargs)

    def display(self, s, f, date, schedule=None):
        if schedule:
            yield from self._display_schedule(s, f, date, schedule)
        else:
            yield from self._display_date(s, f, date)

    @abstractmethod
    def _display_schedule(self, s, f, date, schedule):
        raise NotImplementedError()

    @abstractmethod
    def _display_date(self, s, f, date):
        raise NotImplementedError()


class Reader(BasePipeline):

    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)

    def read(self, s, date, schedule=None):
        if schedule:
            yield from self._read_schedule(s, date, schedule)
        else:
            yield from self._read_date(s, date)

    @abstractmethod
    def _read_schedule(self, s, date, schedule):
        raise NotImplementedError(self.__class__)
        yield

    @abstractmethod
    def _read_date(self, s, date):
        raise NotImplementedError(self.__class__)
        yield


class JournalDiary(Displayer, Reader):

    def _display_date(self, s, f, date):
        start = local_date_to_time(date)
        finish = start + dt.timedelta(days=1)
        for activity_group in s.query(ActivityGroup).order_by(ActivityGroup.sort).all():
            for ajournal in s.query(ActivityJournal). \
                    filter(ActivityJournal.finish >= start,
                           ActivityJournal.start < finish,
                           ActivityJournal.activity_group == activity_group). \
                    order_by(ActivityJournal.start).all():
                yield self._journal_date(s, f, ajournal, date)

    @abstractmethod
    def _journal_date(self, s, f, ajournal, date):
        raise NotImplementedError(self.__class__)

    def _read_date(self, s, date):
        start = local_date_to_time(date)
        finish = start + dt.timedelta(days=1)
        for activity_group in s.query(ActivityGroup).order_by(ActivityGroup.sort).all():
            for ajournal in s.query(ActivityJournal). \
                    filter(ActivityJournal.finish >= start,
                           ActivityJournal.start < finish,
                           ActivityJournal.activity_group == activity_group). \
                    order_by(ActivityJournal.start).all():
                yield list(self._read_journal_date(s, ajournal, date))

    @abstractmethod
    def _read_journal_date(self, s, ajournal, date):
        raise NotImplementedError(self.__class__)
        yield
