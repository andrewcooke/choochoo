
from ..names import FTHR
from ...squeal.tables.constant import Constant
from ...squeal.tables.statistic import StatisticJournal


def hr_zones(log, s, activity_group, time):
    fthr = StatisticJournal.before(s, time, FTHR, Constant, activity_group.id)
    if fthr:
        # values from british cycling online calculator
        # these are upper limits
        return [fthr.value * pc / 100.0 for pc in (68, 83, 94, 105, 121)]
    else:
        return None
