
import datetime as dt
from json import loads

from sqlalchemy import asc, desc

from . import Displayer
from ..calculate.response import Response, ResponseCalculator
from ...diary.model import text, optional_text, value, link
from ...lib.date import local_date_to_time, to_time, format_date
from ...lib.schedule import Schedule
from ...sql.tables.constant import Constant
from ...sql.tables.statistic import StatisticJournal, StatisticName, TYPE_TO_JOURNAL_CLASS


class ResponseDisplayer(Displayer):

    def __init__(self, *args, fitness=None, fatigue=None, **kargs):
        self.fitness = self._assert('fitness', fitness)
        self.fatigue = self._assert('fatigue', fatigue)
        super().__init__(*args, **kargs)

    def _read_date(self, s, date):
        yield from self._read_schedule(s, date, Schedule('d'))

    @optional_text('SHRIMP')
    def _read_schedule(self, s, date, schedule):
        for response in self.fitness + self.fatigue:
            yield from self._read_single(s, date, schedule, response, schedule.frame_type == 'd')
        yield link('Health', db=(format_date(date),))

    def _read_single(self, s, date, schedule, constant_name, display_range, ranges=('all', '90d', '30d')):
        start_time = local_date_to_time(schedule.start_of_frame(date))
        finish_time = local_date_to_time(schedule.next_frame(date))
        response = Response(**loads(Constant.get(s, constant_name).at(s, start_time).value))
        start = self._read(s, response.dest_name, start_time, finish_time, asc)
        finish = self._read(s, response.dest_name, start_time, finish_time, desc)
        if start and finish and start.value != finish.value:
            model = [text(response.dest_name),
                     value('From', int(start.value)), value('To', int(finish.value)),
                     text('⇧' if start.value < finish.value else '⇩')]
            if display_range:
                for range in ranges:
                    limits = self._range(s, response.dest_name, start, finish_time,
                                         None if range == 'all' else dt.timedelta(days=int(range[:-1])))
                    model.append([text(f'Over {range}', tag=range),
                                  value('Lo', int(limits[0].value)), value('Hi', int(limits[1].value))])
            yield model

    @staticmethod
    def _read(s, name, start_time, finish_time, direcn):
        return s.query(StatisticJournal). \
            join(StatisticName). \
            filter(StatisticName.name == name,
                   StatisticName.owner == ResponseCalculator,
                   StatisticJournal.time >= start_time,
                   StatisticJournal.time < finish_time). \
            order_by(direcn(StatisticJournal.time)). \
            limit(1).one_or_none()

    @staticmethod
    def _range(s, name, value, finish_time, period):
        jtype = TYPE_TO_JOURNAL_CLASS[type(value.value)]
        start_time = finish_time - period if period else to_time(0.0)
        q = s.query(jtype). \
            join(StatisticName). \
            filter(StatisticName.name == name,
                   StatisticName.owner == ResponseCalculator,  # todo - owner_in
                   jtype.time >= start_time,
                   jtype.time < finish_time)
        return (q.order_by(asc(jtype.value)).limit(1).one_or_none(),
                q.order_by(desc(jtype.value)).limit(1).one_or_none())
