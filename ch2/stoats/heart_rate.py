
from .names import FTHR
from ..squeal.tables.constant import ConstantJournal


def hr_zones(log, s, time):
    fthr = ConstantJournal.lookup(log, s, FTHR, time)
    if fthr:
        # values from british cycling online calculator
        # these are upper limits
        return [fthr.value * pc / 100.0 for pc in (68, 83, 94, 105, 121)]
    else:
        return None
