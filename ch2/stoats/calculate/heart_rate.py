
from ..names import FTHR
from ...squeal.tables.constant import ConstantJournal


def hr_zones(log, s, activity_group, time):
    fthr = ConstantJournal.lookup_statistic_journal(log, s, FTHR, activity_group.id, time)
    if fthr:
        # values from british cycling online calculator
        # these are upper limits
        return [fthr.value * pc / 100.0 for pc in (68, 83, 94, 105, 121)]
    else:
        return None
