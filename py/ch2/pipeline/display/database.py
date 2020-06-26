
from logging import getLogger

from sqlalchemy.sql.functions import count

from .utils import Displayer
from ...diary.model import value, optional_text, text
from ...global_ import global_data
from ...sql import Interval

log = getLogger(__name__)


class DatabaseDisplayer(Displayer):

    @optional_text('Database')
    def _read_date(self, s, date):
        q = s.query(Interval.id).filter(Interval.dirty == True)
        total = q.count()
        today = q.filter(Interval.start <= date, Interval.finish > date).count()
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
