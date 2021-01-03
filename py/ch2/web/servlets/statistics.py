from ch2.common.date import time_to_local_time
from ch2.names import N
from ch2.pipeline.calculate import SummaryCalculator, ElevationCalculator
from ch2.pipeline.calculate.power import PowerCalculator
from ch2.pipeline.read.activity import ActivityReader
from ch2.sql import StatisticName, StatisticJournal, StatisticJournalType
from ch2.sql.types import short_cls


class Statistics:

    def read_all_plottable(self, request, s):
        q = s.query(StatisticName). \
            filter(StatisticName.statistic_journal_type.in_(
            [StatisticJournalType.FLOAT, StatisticJournalType.INTEGER]),
            ~StatisticName.owner.in_([SummaryCalculator, ActivityReader])). \
            order_by(StatisticName.name)
        return [{'name': name.name, 'title': name.title, 'owner': name.owner}
                for name in q.all() if not (
                    (name.owner == short_cls(PowerCalculator)
                     and name.name in [N.POWER_ESTIMATE, N.CLIMB_POWER, N.HEADING, N.VERTICAL_POWER])
                    or
                    (name.owner == short_cls(ElevationCalculator)
                     and name.name in [N.ELEVATION, N.GRADE]))]

    def read_values(self, request, s, name):
        statistic_name = self._resolve_name(request, s, name)
        values = s.query(StatisticJournal). \
            filter(StatisticJournal.statistic_name == statistic_name). \
            order_by(StatisticJournal.time)
        return [{'date': time_to_local_time(value.time),
                 'value': value.value} for value in values]

    def _resolve_name(self, request, s, name):
        owner = request.args.get('owner', None)
        q = s.query(StatisticName).filter(StatisticName.name == name)
        if owner:
            q = q.filter(StatisticName.owner == owner)
        n = q.count()
        if n == 0:
            raise Exception(f'No such statistic ({name}/{owner})')
        if n > 1:
            owners = ', '.join(sn.owner for sn in q.all())
            raise Exception(f'Statistic {name} has multiple owners ({owners})')
        return q.one()
