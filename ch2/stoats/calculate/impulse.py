
import datetime as dt
from collections import namedtuple
from json import loads
from logging import getLogger
from math import exp

from sqlalchemy import desc, inspect, select, and_

from . import IntervalCalculatorMixin, UniProcCalculator
from .heart_rate import HRImpulse
from ..names import MAX
from ...commands.args import FINISH, START
from ...lib.date import local_date_to_time
from ...squeal import Constant, Interval, StatisticJournal, StatisticName, StatisticJournalFloat

log = getLogger(__name__)

# constraint comes from constant
Response = namedtuple('Response', 'src_name, src_owner, dest_name, tau_days, scale, start')


class ImpulseCalculator(IntervalCalculatorMixin, UniProcCalculator):

    def __init__(self, *args, responses=None, impulse=None, **kargs):
        self.responses_ref = self._assert('responses', responses)
        self.impulse_ref = self._assert('impulse', impulse)
        super().__init__(*args, **kargs)

    def _startup(self, s):
        super()._startup(s)
        existing, _ = Interval.first_missing_date(log, s, self.schedule, self.owner_out)
        if self.force:
            if self.start and self.start > existing:
                log.debug(f'Extending {START}={self.start} to {existing}')
                self.start = existing
        else:
            if self.start:
                if self.start < existing:
                    log.debug(f'Restricting {START}={self.start} to {existing}')
                    self.start = existing
            else:
                log.debug(f'Setting {START}={existing}')
                self.start = existing
            log.debug(f'Deleting to ensure continuous missing data')
            self.force = True
        if self.finish:
            log.debug(f'Discarding {FINISH}={self.finish}')
            self.finish = None
        self.constants = [Constant.get(s, response) for response in self.responses_ref]
        self.responses = [Response(**loads(constant.at(s).value)) for constant in self.constants]
        self.impulse = HRImpulse(**loads(Constant.get(s, self.impulse_ref).at(s).value))

    def _read_data(self, s, interval):
        for response, constant in zip(self.responses, self.constants):
            activity_group = constant.statistic_name.constraint
            source = s.query(StatisticName). \
                filter(StatisticName.name == self.impulse.dest_name,
                       StatisticName.owner == self.owner_in,
                       StatisticName.constraint == activity_group).one_or_none()
            if source:  # None if no data loaded
                yield response, source, list(self._impulses(s, source, interval))
            else:
                log.warning(f'No values for {self.impulse.dest_name}')

    def _impulses(self, s, source, interval):
        sj = inspect(StatisticJournal).local_table
        sjf = inspect(StatisticJournalFloat).local_table

        stmt = select([sj.c.time, sjf.c.value]). \
            select_from(sj.join(sjf)). \
            where(and_(sj.c.statistic_name_id == source.id,
                       sj.c.time >= local_date_to_time(interval.start),
                       sj.c.time < local_date_to_time(interval.finish))). \
            order_by(desc(sj.c.time))
        return s.connection().execute(stmt)

    def _calculate_results(self, s, interval, data, loader):
        for response, source, impulses in data:
            self._calculate_response(s, interval, response, source, impulses, loader)

    def _calculate_response(self, s, interval, response, source, impulses, loader):
        log.debug(f'Calculating {response.dest_name} for {interval}')
        if self._prev_loader:
            prev = self._prev_loader.latest(response.dest_name, source.constraint)
        else:
            prev = self._previous(s, response.dest_name, interval.start)
        if prev:
            value = prev.time, prev.value
        else:
            value = None
        days = list(self._hours(interval))
        prev_time = None
        # move hours very slightly later in sort so that we can de-duplicate times
        for time, impulse in sorted(impulses + days,
                                    key=lambda x: x[0] +
                                                  (dt.timedelta(seconds=0.01) if x[1] is None else dt.timedelta())):
            if prev_time is None or time != prev_time:
                if impulse:
                    if not value:
                        value = (time, response.start)
                    else:
                        value = self._decay(response, value, time)
                    value = (time, value[1] + response.scale * impulse)
                    loader.add(response.dest_name, None, MAX, source.constraint, interval, value[1], value[0],
                               StatisticJournalFloat)
                else:
                    if value:
                        value = self._decay(response, value, time)
                        loader.add(response.dest_name, None, MAX, source.constraint, interval, value[1], value[0],
                                   StatisticJournalFloat)
            prev_time = time

    def _previous(self, s, dest, start):
        return s.query(StatisticJournal). \
            join(StatisticName). \
            filter(StatisticName.name == dest,
                   StatisticJournal.time < local_date_to_time(start)). \
            order_by(desc(StatisticJournal.time)).limit(1).one_or_none()

    def _decay(self, response, value, time):
        dt = (time - value[0]).total_seconds()
        return time, value[1] * exp(-dt / (response.tau_days * 24 * 60 * 60))

    def _hours(self, interval):
        day = interval.start
        while day < interval.finish:
            start = local_date_to_time(day)
            for hours in range(24):
                yield start + dt.timedelta(hours=hours), None
            day += dt.timedelta(days=1)
