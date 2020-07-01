
import datetime as dt

from sqlalchemy import asc, desc

from .utils import Displayer
from ..pipeline import OwnerInMixin
from ...diary.model import text, optional_text, value, link
from ...common.date import local_date_to_time, to_time, format_date
from ...lib.schedule import Schedule
from ...sql.tables.statistic import StatisticJournal, StatisticName, TYPE_TO_JOURNAL_CLASS


class ResponseDisplayer(OwnerInMixin, Displayer):

    def __init__(self, *args, prefix=None, **kargs):
        self.prefix = self._assert('prefix', prefix)
        super().__init__(*args, **kargs)

    def __statistic_names(self, s):
        return s.query(StatisticName). \
            filter(StatisticName.owner == self.owner_in,
                   StatisticName.name.like(self.prefix + '%')).all()

    def _read_date(self, s, date):
        yield from self._read_schedule(s, date, Schedule('d'))

    @optional_text('SHRIMP')
    def _read_schedule(self, s, date, schedule):
        for statistic_name in self.__statistic_names(s):
            yield from self._read_single(s, date, schedule, statistic_name, schedule.frame_type == 'd')
        yield link('Health', db=(format_date(date),))

    def _read_single(self, s, date, schedule, statistic_name, display_range, ranges=('all', '90d', '30d')):
        start_time = local_date_to_time(schedule.start_of_frame(date))
        finish_time = local_date_to_time(schedule.next_frame(date))
        start = self._read(s, statistic_name, start_time, finish_time, asc)
        finish = self._read(s, statistic_name, start_time, finish_time, desc)
        if start and finish and start.value != finish.value:
            model = [text(statistic_name.title),
                     value('From', int(start.value)), value('To', int(finish.value)),
                     text('⇧' if start.value < finish.value else '⇩')]
            if display_range:
                for range in ranges:
                    limits = self._range(s, statistic_name, start, finish_time,
                                         None if range == 'all' else dt.timedelta(days=int(range[:-1])))
                    model.append([text(f'Over {range}', tag=range),
                                  value('Lo', int(limits[0].value)), value('Hi', int(limits[1].value))])
            yield model

    def _read(self, s, statistic_name, start_time, finish_time, direcn):
        return s.query(StatisticJournal). \
            filter(StatisticJournal.statistic_name == statistic_name,
                   StatisticJournal.time >= start_time,
                   StatisticJournal.time < finish_time). \
            order_by(direcn(StatisticJournal.time)).first()

    def _range(self, s, statistic_name, value, finish_time, period):
        jtype = TYPE_TO_JOURNAL_CLASS[type(value.value)]
        start_time = finish_time - period if period else to_time(0.0)
        q = s.query(jtype). \
            filter(jtype.statistic_name == statistic_name,
                   jtype.time >= start_time,
                   jtype.time < finish_time)
        return (q.order_by(asc(jtype.value)).first(),
                q.order_by(desc(jtype.value)).first())
