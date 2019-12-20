
import datetime as dt
from json import loads

from sqlalchemy import asc, desc
from urwid import Pile, Text, Columns

from . import Displayer, Reader
from ..calculate.response import Response, ResponseCalculator
from ...diary.model import text, optional_label, value
from ...lib.date import local_date_to_time, to_time
from ...lib.schedule import Schedule
from ...lib.utils import label, em, error
from ...sql.tables.constant import Constant
from ...sql.tables.statistic import StatisticJournal, StatisticName, TYPE_TO_JOURNAL_CLASS
from ...urwid.tui.decorators import Indent


class ResponseDiary(Displayer, Reader):

    def __init__(self, *args, fitness=None, fatigue=None, **kargs):
        self.fitness = self._assert('fitness', fitness)
        self.fatigue = self._assert('fatigue', fatigue)
        super().__init__(*args, **kargs)

    def _display_date(self, s, f, date):
        yield from self._display_schedule(s, f, date, Schedule('d'))

    @optional_label('SHRIMP')
    def _read_date(self, s, date):
        yield from self._read_schedule(s, date, Schedule('d'))

    def _read_schedule(self, s, date, schedule):
        for response in self.fitness + self.fatigue:
            yield from self._read_single(s, date, schedule, response, schedule.frame_type == 'd')

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

    def _display_schedule(self, s, f, date, schedule):
        rows = []
        for fitness in self.fitness:
            for cols in self._single_response(s, f, date, schedule, fitness, schedule.frame_type == 'd'):
                rows.append(Columns(cols))
        for fatigue in self.fatigue:
            for cols in self._single_response(s, f, date, schedule, fatigue, schedule.frame_type == 'd'):
                rows.append(Columns(cols))
        if rows:
            yield Pile([Text('SHRIMP'), Indent(Pile(rows))])

    def _single_response(self, s, f, date, schedule, constant_name, display_range, ranges=('all', '90d', '30d')):
        start_time = local_date_to_time(schedule.start_of_frame(date))
        finish_time = local_date_to_time(schedule.next_frame(date))
        response = Response(**loads(Constant.get(s, constant_name).at(s, start_time).value))
        start = self._read(s, response.dest_name, start_time, finish_time, asc)
        finish = self._read(s, response.dest_name, start_time, finish_time, desc)
        if start and finish and start.value != finish.value:
            no_range = [Text(response.dest_name),
                        Text([label('Frm: '), f'{int(start.value)}']),
                        Text([label('To:  '), f'{int(finish.value)}']),
                        Text(em('increase') if start.value < finish.value else error('decrease'))]
            if not display_range:
                yield no_range
            else:
                limits = [self._range(s, response.dest_name, start, finish_time,
                                      None if range == 'all' else dt.timedelta(days=int(range[:-1])))
                          for range in ranges]
                if any(any(value is None for value in limit) for limit in limits):
                    yield no_range
                else:
                    # use first range for quintiles
                    lo, hi = limits[0]
                    style = 'quintile-%d' % min(5, 1 + int(5 * (finish.value - lo.value) / (hi.value - lo.value)))
                    yield [Text(response.dest_name),
                           Text([label('Frm: '), (style, '%d' % int(start.value))]),
                           Text([label('To:  '), (style, '%d' % int(finish.value))]),
                           Text(em('increase') if start.value < finish.value else error('decrease'))]
                    yield [Text([label(f'Over {",".join(str(range) for range in ranges)}')]),
                           Text([label('Lo:  '), ','.join(str(int(lo.value)) for lo, hi in limits)]),
                           Text([label('Hi:  '), ','.join(str(int(hi.value)) for lo, hi in limits)]),
                           Text('')]

    def _read(self, s, name, start_time, finish_time, direcn):
        return s.query(StatisticJournal). \
            join(StatisticName). \
            filter(StatisticName.name == name,
                   StatisticName.owner == ResponseCalculator,
                   StatisticJournal.time >= start_time,
                   StatisticJournal.time < finish_time). \
            order_by(direcn(StatisticJournal.time)). \
            limit(1).one_or_none()

    def _range(self, s, name, value, finish_time, period):
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
