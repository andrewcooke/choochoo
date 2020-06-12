
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
        ids = set(d.interval_id for d in global_data().sys.get_dirty_intervals())
        total = s.query(count(Interval.id)).filter(Interval.id.in_(ids)).count()
        today = s.query(count(Interval.id)). \
            filter(Interval.id.in_(ids),
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
