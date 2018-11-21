
import datetime as dt
from collections import namedtuple
from json import loads
from math import exp

from sqlalchemy import desc, inspect, select, and_

from . import IntervalCalculator
from ..load import Loader
from ...lib.date import local_date_to_time
from ...lib.schedule import Schedule
from ...squeal.database import add
from ...squeal.tables.constant import Constant
from ...squeal.tables.source import Interval
from ...squeal.tables.statistic import StatisticJournal, StatisticName, StatisticJournalFloat
from ...squeal.types import short_cls

SCHEDULE = Schedule('m')

# constraint comes from constant
Response = namedtuple('Response', 'src_name, src_owner, dest_name, tau_days, scale, start')
HRImpulse = namedtuple('HRImpulse', 'dest_name, gamma, zero')


class ImpulseStatistics(IntervalCalculator):

    # todo - NEED TO DELETE FORWARDS

    # todo - delete intervals manually

    def _filter_intervals(self, q, responses=None, impulse=None):
        return q.filter(Interval.schedule == SCHEDULE,
                        Interval.owner == self)

    def _previous(self, s, name, start):
        prev = s.query(StatisticJournal). \
            join(StatisticName). \
            filter(StatisticName.name == name,
                   StatisticJournal.time < local_date_to_time(start)). \
            order_by(desc(StatisticJournal.time)).limit(1).one_or_none()
        if prev:
            return prev.time, prev.value
        else:
            return None

    def _impulses(self, s, source, interval):

        sj = inspect(StatisticJournal).local_table
        sjf = inspect(StatisticJournalFloat).local_table

        stmt = select([sj.c.time, sjf.c.value]). \
            select_from(sj.join(sjf)). \
            where(and_(sj.c.statistic_name_id == source.id,
                       sj.c.time >= local_date_to_time(interval.start),
                       sj.c.time < local_date_to_time(interval.finish))). \
            order_by(desc(sj.c.time))
        # self._log.debug(stmt)
        return s.connection().execute(stmt)

    def _decay(self, response, value, time):
        dt = (time - value[0]).total_seconds()
        return time, value[1] * exp(-dt / (response.tau_days * 24 * 60 * 60))

    def _days(self, interval):
        day = interval.start
        while day < interval.finish:
            yield local_date_to_time(day), None
            day += dt.timedelta(days=1)

    def _add_response(self, loader, s, response, interval, source):
        value = self._previous(s, response.dest_name, interval.start)
        impulses = list(self._impulses(s, source, interval))
        days = list(self._days(interval))
        for time, impulse in sorted(impulses + days, key=lambda x: x[0]):
            if impulse:
                if not value:
                    value = (time, response.start)
                else:
                    value = self._decay(response, value, time)
                value = (time, value[1] + response.scale * impulse)
            else:
                if value:
                    value = self._decay(response, value, time)
                    loader.add(response.dest_name, None, None, source.constraint, interval, value[1], value[0],
                               StatisticJournalFloat)

    def _run_calculations(self, responses=None, impulse=None):

        from .heart_rate import HeartRateStatistics

        with self._db.session_context() as s:

            loader = Loader(self._log, s, self)
            constants = [Constant.get(s, response) for response in responses]
            responses = [Response(**loads(constant.at(s).value)) for constant in constants]
            impulse = HRImpulse(**loads(Constant.get(s, impulse).at(s).value))

            for start, finish in Interval.missing_dates(self._log, s, SCHEDULE, self):
                interval = add(s, Interval(start=start, finish=finish, schedule=SCHEDULE, owner=self))
                self._log.info('Running %s for %s' % (short_cls(self), interval))
                for response, constant in zip(responses, constants):
                    activity_group = constant.statistic_name.constraint
                    source = s.query(StatisticName). \
                        filter(StatisticName.name == impulse.dest_name,
                               StatisticName.owner == HeartRateStatistics,
                               StatisticName.constraint == activity_group).one()
                    self._add_response(loader, s, response, interval, source)

            loader.load()
