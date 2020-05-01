
from logging import getLogger

from .model import text, value
from ..lib import to_date
from ..lib.date import YMD
from ..pipeline.calculate.summary import SummaryCalculator
from ..pipeline.display.display import log, Displayer
from ..sql import StatisticJournal, Pipeline, PipelineType

log = getLogger(__name__)


def read_date(s, date):
    yield text(date.strftime('%Y-%m-%d - %A'), tag='title')
    yield from read_pipeline(s, date)


def read_schedule(s, schedule, date):
    yield text(date.strftime(YMD) + ' - Summary for %s' % schedule.describe(), tag='title')
    yield from read_pipeline(s, date, schedule=schedule)


def summary_column(s, schedule, start, name):
    journals = StatisticJournal.at_interval(s, start, schedule, SummaryCalculator, name, SummaryCalculator)
    for named, journal in enumerate(journal for journal in journals if journal.value != 0):
        summary, period, name = SummaryCalculator.parse_name(journal.statistic_name.name)
        if not named:
            yield text(name)
        yield value(summary, journal.value, units=journal.statistic_name.units)


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
