
from itertools import groupby

from ..calculate.activity import ActivityCalculator
from ..names import CLIMB_ELEVATION, TOTAL_CLIMB
from ...squeal import StatisticJournal, StatisticName


def climbs_for_activity(s, ajournal):
    total = s.query(StatisticJournal).join(StatisticName). \
        filter(StatisticName.name == TOTAL_CLIMB,
               StatisticJournal.time == ajournal.start,
               StatisticName.owner == ActivityCalculator,
               StatisticName.constraint == ajournal.activity_group).order_by(StatisticJournal.time).one_or_none()
    statistics = s.query(StatisticJournal).join(StatisticName). \
        filter(StatisticName.name.like('Climb %'),
               StatisticJournal.time >= ajournal.start,
               StatisticJournal.time <= ajournal.finish,
               StatisticName.owner == ActivityCalculator,
               StatisticName.constraint == ajournal.activity_group).order_by(StatisticJournal.time).all()
    return total, sorted((dict((statistic.statistic_name.name, statistic) for statistic in climb_statistics)
                          for _, climb_statistics in groupby(statistics, key=lambda statistic: statistic.time)),
                         key=lambda climb: climb[CLIMB_ELEVATION].value, reverse=True)
