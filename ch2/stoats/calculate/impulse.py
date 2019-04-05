
import datetime as dt
from collections import namedtuple
from json import loads
from logging import getLogger
from math import exp

from sqlalchemy import desc, select, and_

from . import UniProcCalculator, CompositeCalculatorMixin
from .heart_rate import HRImpulse
from ..names import MAX
from ...data.frame import _tables
from ...lib.date import local_date_to_time
from ...squeal import Constant, StatisticJournal, StatisticName, StatisticJournalFloat, ActivityJournal

log = getLogger(__name__)

# constraint comes from constant
Response = namedtuple('Response', 'src_name, src_owner, dest_name, tau_days, scale, start')

State = namedtuple('State', 'prev_time, prev_value')


class ImpulseCalculator(CompositeCalculatorMixin, UniProcCalculator):

    def __init__(self, *args, responses=None, impulse=None, **kargs):
        self.responses_ref = self._assert('responses', responses)
        self.impulse_ref = self._assert('impulse', impulse)
        self.__state = {}
        self.__impulse_id = None
        self.__prev_source_id = None
        super().__init__(*args, **kargs)

    def _startup(self, s):
        super()._startup(s)
        self.constants = [Constant.get(s, response) for response in self.responses_ref]
        self.responses = [Response(**loads(constant.at(s).value)) for constant in self.constants]
        self.impulse = HRImpulse(**loads(Constant.get(s, self.impulse_ref).at(s).value))

    def _missing(self, s):
        self.__impulse_id = s.query(StatisticName.id). \
            filter(StatisticName.name == self.impulse.dest_name,
                   StatisticName.owner == self.owner_in).scalar()
        log.debug(f'Impulse ID: {self.__impulse_id}')
        try:
            dates = super()._missing(s)
            if dates:
                # need to delete forwards just in case there's some weird gap
                log.info('Need to delete forwards for Impulse')
                self._delete_time_range(s, local_date_to_time(dates[0]), 0)
                dates = super()._missing(s)
                return list(self.__days(dates[0], dates[-1]))
            else:
                return []
        finally:
            self.__set_state(s)

    def __days(self, start, finish):
        day = dt.timedelta(days=1)
        while start <= finish:
            yield start
            start += day

    def _unused_sources_given_used(self, s, used_sources):
        sources = s.query(ActivityJournal). \
            join(StatisticJournal, StatisticName). \
            filter(~ActivityJournal.id.in_(used_sources),
                   StatisticName.id == self.__impulse_id)
        start, finish = self._start_finish(local_date_to_time)
        if start:
            sources = sources.filter(ActivityJournal.finish >= start)
        if finish:
            sources = sources.filter(ActivityJournal.start <= finish)
        log.debug(f'Unused query: {sources}')
        return sources.all()

    def __set_state(self, s):
        for response, constant in zip(self.responses, self.constants):
            start, finish = self._start_finish(local_date_to_time)
            name = response.dest_name
            activity_group = constant.statistic_name.constraint
            prev = s.query(StatisticJournal). \
                join(StatisticName). \
                filter(StatisticName.name == name,
                       StatisticName.owner == self.owner_out,
                       StatisticName.constraint == activity_group). \
                order_by(desc(StatisticJournal.time)).limit(1).one_or_none()
            prev_time = prev.time if prev else start
            prev_value = prev.value if prev else 1e-20  # avoid zero as it gives numerical issues later
            self.__state[name] = State(prev_time=prev_time, prev_value=prev_value)
            log.debug(f'State for {name}: {self.__state[name]}')
            if not self.__prev_source_id:
                self.__prev_source_id = prev.source_id if prev else None
                log.debug(f'Source ID: {self.__prev_source_id}')

    def _read_data(self, s, start, finish):
        impulses, t, source_ids = {}, _tables(), set()
        for response, constant in zip(self.responses, self.constants):
            name = response.dest_name
            stmt = select([t.sj.c.time, t.sj.c.source_id, t.sjf.c.value]). \
                select_from(t.sj.join(t.sjf)). \
                where(and_(t.sj.c.statistic_name_id == self.__impulse_id,
                           t.sj.c.time >= start,
                           t.sj.c.time < finish)). \
                order_by(t.sj.c.time)
            rows = list(s.connection().execute(stmt))
            impulses[name] = [(row[0], row[2]) for row in rows]
            source_ids.update(row[1] for row in rows)
        if self.__prev_source_id:
            source_ids.add(self.__prev_source_id)
        return source_ids, impulses

    def _calculate_results(self, s, source, data, loader, start, finish):
        for response, constant in zip(self.responses, self.constants):
            name = response.dest_name
            impulses = data[name]
            prev_time, value = self.__state[name]
            for time, impulse in self.__pad(impulses, start, finish):
                if prev_time:
                    dt = (time - prev_time).total_seconds()
                    value *= exp(-dt / (response.tau_days * 24 * 60 * 60))
                value += response.scale * impulse
                # log.debug(f'{time}: {value}')
                loader.add(response.dest_name, None, MAX, constant.statistic_name.constraint, source, value, time,
                           StatisticJournalFloat)
                prev_time = time
            self.__state[name] = self.__state[name]._replace(prev_time=prev_time, prev_value=value)
        self.__prev_source_id = source.id
        log.debug(f'Source ID: {self.__prev_source_id}')

    def __pad(self, impulses, start, finish):
        delta = dt.timedelta(hours=1)  # every hour is assumed by data.frame.std_health_statistics
        for (time, impulse) in impulses:
            while start < time:
                yield start, 0
                start += delta
            yield time, impulse
            start = time + delta
        while start < finish:
            yield start, 0
            start += delta
