
import datetime as dt
from collections import namedtuple
from math import exp

from sqlalchemy import desc

from . import IntervalCalculator
from ...lib.date import local_date_to_time
from ...lib.schedule import Schedule
from ...squeal.database import add
from ...squeal.tables.source import Interval
from ...squeal.tables.statistic import StatisticJournal, StatisticName, StatisticJournalFloat

SCHEDULE = Schedule('w')

Response = namedtuple('Response', 'name, tau, scale, start')

Impulse = namedtuple('Impulse', 'name, owner, constraint')


class ImpulseStatistics(IntervalCalculator):

    # implement this as a weekly interval - try to avoid daily intervals as there will be lots,
    # but keep fairly short to reduce amount of work on re-calculation.

    # BUT NEED TO DELETE FORWARDS

    def _filter_intervals(self, responses=None, impulse=None):
        return q.filter(Interval.schedule == SCHEDULE,
                        Interval.owner == self)

    def _previous(self, s, result, start):
        prev = s.query(StatisticJournal). \
            filter(StatisticJournal.statistic_name == result,
                   StatisticJournal.time < local_date_to_time(start)). \
            order_by(desc(StatisticJournal.time)).limit(1).one_or_none()
        if prev:
            return prev.time, prev.value
        else:
            return None

    def _impulses(self, s, source, interval):
        return [(impulse.time, impulse.value) for impulse in
                s.query(StatisticJournal).
                    filter(StatisticJournal.statistic_name == source,
                           StatisticJournal.time >= local_date_to_time(interval.start),
                           StatisticJournal.time < local_date_to_time(interval.finish)).
                    order_by(desc(StatisticJournal.time)).all()]

    def _decay(self, response, value, time):
        dt = (time - value[0]).total_seconds()
        return time, value[1] * exp(-dt / response.tau)

    def _days(self, interval):
        day = interval.start
        while day < interval.finish:
            yield local_date_to_time(day), None
            day += dt.timedelta(days=1)

    def _add_response(self, s, response, interval, source, result):
        value = self._previous(s, result, interval.start)
        impulses = self._impulses(s, source, interval)
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
                    add(s, StatisticJournalFloat(statistic_name=result, source=interval, time=value[0], value=value[1]))

    def _run_calculations(self, responses=None, impulse=None):
        responses = [Response(**response) for response in responses]
        impulse = Impulse(**impulse)
        with self._db.session_context() as s:
            for start, finish in Interval.missing_dates(self._log, s, SCHEDULE, self):
                interval = add(s, Interval(start=start, finish=finish, schedule=SCHEDULE, owner=self))
                for response in responses:
                    source = s.query(StatisticName). \
                        filter(StatisticName.name == impulse.name,
                               StatisticName.owner == impulse.owner,
                               StatisticName.constraint == impulse.constraint).one()
                    result = StatisticJournal.add_name(self._log, s, response.name, None, None, self, impulse)
                    self._add_response(s, response, interval, source, result)
