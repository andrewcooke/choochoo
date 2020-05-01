
import datetime as dt
from abc import abstractmethod
from logging import getLogger

from ...lib.date import local_date_to_time, to_date
from ...lib.log import log_current_exception
from ...sql import ActivityGroup, ActivityJournal
from ...sql.tables.pipeline import Pipeline, PipelineType
from ...stats.pipeline import BasePipeline

log = getLogger(__name__)


def read_pipeline(session, date, schedule=None):
    '''
    schedule only sent for summary views.
    '''
    date = to_date(date)   # why is this needed?
    for pipeline in Pipeline.all(session, PipelineType.DIARY):
        log.info(f'Building {pipeline.cls} ({pipeline.args}, {pipeline.kargs})')
        instance = pipeline.cls(*pipeline.args, **pipeline.kargs)
        if isinstance(instance, Displayer):
            data = list(instance.read(session, date, schedule=schedule))
            if data:
                yield data


class Displayer(BasePipeline):

    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)

    def read(self, s, date, schedule=None):
        try:
            if schedule:
                yield from self._read_schedule(s, date, schedule)
            else:
                yield from self._read_date(s, date)
        except Exception as e:
            log_current_exception(e)

    @abstractmethod
    def _read_schedule(self, s, date, schedule):
        raise NotImplementedError(self.__class__.__name__)
        yield

    @abstractmethod
    def _read_date(self, s, date):
        raise NotImplementedError(self.__class__.__name__)
        yield


class ActivityJournalDelegate:

    def __init__(self, interpolate=False):
        self.interpolate = interpolate

    @abstractmethod
    def read_journal_date(self, s, ajournal, date):
        raise NotImplementedError(self.__class__.__name__)
        yield

    @abstractmethod
    def read_schedule(self, s, date, schedule):
        raise NotImplementedError(self.__class__.__name__)
        yield



class JournalDiary(Displayer):

    def _read_date(self, s, date):
        start = local_date_to_time(date)
        finish = start + dt.timedelta(days=1)
        for activity_group in s.query(ActivityGroup).order_by(ActivityGroup.sort).all():
            for ajournal in s.query(ActivityJournal). \
                    filter(ActivityJournal.finish >= start,
                           ActivityJournal.start < finish,
                           ActivityJournal.activity_group == activity_group). \
                    order_by(ActivityJournal.start).all():
                yield from self._read_journal_date(s, ajournal, date)

    @abstractmethod
    def _read_journal_date(self, s, ajournal, date):
        raise NotImplementedError(self.__class__)
        yield
