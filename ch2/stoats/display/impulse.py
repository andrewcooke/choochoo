
import datetime as dt
from json import loads

from sqlalchemy import asc, desc
from urwid import Pile, Text, Columns

from . import Displayer
from ..calculate.impulse import Response, ImpulseCalculator
from ...lib.date import local_date_to_time
from ...lib.schedule import Schedule
from ...lib.utils import label, em, error
from ...squeal.tables.constant import Constant
from ...squeal.tables.statistic import StatisticJournal, StatisticName, TYPE_TO_JOURNAL_CLASS
from ...uweird.tui.decorators import Indent


class ImpulseDiary(Displayer):

    def __init__(self, *args, fitness=None, fatigue=None, **kargs):
        self.fitness = self._assert('fitness', fitness)
        self.fatigue = self._assert('fatigue', fatigue)
        super().__init__(*args, **kargs)

    def _display_date(self, s, f, date):
        yield from self._display_schedule(s, f, date, schedule=Schedule('d'))

    def _display_schedule(self, s, f, date, schedule=None):
        rows = []
        for fitness in self.fitness:
            for cols in self._single_response(s, f, date, schedule, fitness, schedule.frame_type == 'd'):
                rows.append(Columns(cols))
        for fatigue in self.fatigue:
            for cols in self._single_response(s, f, date, schedule, fatigue, schedule.frame_type == 'd'):
                rows.append(Columns(cols))
        if rows:
            yield Pile([Text('SHRIMP'), Indent(Pile(rows))])

    def _single_response(self, s, f, date, schedule, constant_name, display_range):
        start_time = local_date_to_time(schedule.start_of_frame(date))
        finish_time = local_date_to_time(schedule.next_frame(date))
        response = Response(**loads(Constant.get(s, constant_name).at(s, start_time).value))
        start = self._read(s, response.dest_name, start_time, finish_time, asc)
        finish = self._read(s, response.dest_name, start_time, finish_time, desc)
        if start and finish and start.value != finish.value:
            lo, hi = self._range(s, response.dest_name, start, finish_time, dt.timedelta(days=90))
            if lo is not None and hi is not None:
                if display_range:
                    style = 'quintile-%d' % min(5, 1 + int(5 * (finish.value - lo.value) / (hi.value - lo.value)))
                else:
                    style = 'em'
                yield [Text(response.dest_name),
                       Text([label('Frm: '), (style, '%d' % int(start.value))]),
                       Text([label('To:  '), (style, '%d' % int(finish.value))]),
                       Text(em('increase') if start.value < finish.value else error('decrease'))]
                if display_range:
                    yield [Text([label('Over 90 days')]),
                           Text([label('Lo:  '), '%d' % int(lo.value)]),
                           Text([label('Hi:  '), '%d' % int(hi.value)]),
                           Text('')]

    def _read(self, s, name, start_time, finish_time, direcn):
        return s.query(StatisticJournal). \
            join(StatisticName). \
            filter(StatisticName.name == name,
                   StatisticName.owner == ImpulseCalculator,
                   StatisticJournal.time >= start_time,
                   StatisticJournal.time < finish_time). \
            order_by(direcn(StatisticJournal.time)). \
            limit(1).one_or_none()

    def _range(self, s, name, value, finish_time, period):
        jtype = TYPE_TO_JOURNAL_CLASS[type(value.value)]
        start_time = finish_time - period
        q = s.query(jtype). \
            join(StatisticName). \
            filter(StatisticName.name == name,
                   StatisticName.owner == ImpulseCalculator,  # todo - owner_in
                   jtype.time >= start_time,
                   jtype.time < finish_time)
        return (q.order_by(asc(jtype.value)).limit(1).one_or_none(),
                q.order_by(desc(jtype.value)).limit(1).one_or_none())
