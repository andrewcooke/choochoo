
from logging import getLogger

from sqlalchemy.sql.functions import count

from . import Displayer
from ..calculate.monitor import MonitorCalculator
from ..names import REST_HR, DAILY_STEPS
from ...diary.database import summary_column
from ...diary.model import value, optional_text, text
from ...sql import Interval
from ...sql.tables.statistic import StatisticJournal, StatisticName

log = getLogger(__name__)


class DatabaseDisplayer(Displayer):

    @optional_text('Database')
    def _read_date(self, s, date):
        total = s.query(count(Interval.id)).filter(Interval.dirty == True).scalar()
        today = s.query(count(Interval.id)). \
            filter(Interval.dirty == True,
                   Interval.start <= date,
                   Interval.finish > date).scalar()
        if not total:
            yield text('No dirty statistics')
        else:
            if today:
                yield value('Dirty statistics today', today)
            yield value('Total dirty statistics', total)
            yield text('Recalculate statistics')

    def _read_schedule(self, s, date, schedule):
        # todo - include?
        return
        yield
