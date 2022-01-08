
from math import exp

from ..lib import to_time
from ..sql import StatisticJournal, Constant, ActivityGroup
from ..names import N

# values from british cycling online calculator
# these are upper limits; 1-5 from BC; 0 extrapolated backwards from 1-2
BC_ZONES = (68 - (83-68), 68, 83, 94, 105, 121)


# these functions were used during development, but are not used in current code
# which does calculations on dataframes for efficiency.
# they have been left for documentation (and possibly useful from jupyter).


def zone(hr, fthr, zones=BC_ZONES):
    zones = [x * fthr / 100.0 for x in zones]
    for i in range(len(zones)):
        if hr < zones[i]:
            if i == len(zones) - 1:
                return i + (hr - zones[i-1]) / (zones[i-1] - zones[i-2])
            elif i:
                return i + (hr - zones[i-1]) / (zones[i] - zones[i-1])
            else:
                return 1 + (hr - zones[0]) / (zones[1] - zones[0])
    return len(zones)


def shrimp(hr, gamma, zero, fthr, zones=BC_ZONES):
    hrz = zone(hr, fthr, zones)
    n = len(zones)
    return n * (max(0, hrz - zero) / (n - zero)) ** gamma


def trimp(hr, rest_hr, max_hr, k):
    x = (hr - rest_hr) / (max_hr - rest_hr)
    return x * 0.64 * exp(k * x)


def edwards(hr, max_hr):
    return max(0, int(10 * (1 - (max_hr - hr) / max_hr)) - 4)


def hr_zones_from_database(s, local_time, activity_group):
    activity_group = ActivityGroup.from_name(s, activity_group)
    fthr = StatisticJournal.before(s, to_time(local_time), N.FTHR, Constant, activity_group)
    if fthr:
        return hr_zones(fthr.value)
    else:
        return None


def hr_zones(fthr):
    return [fthr * pc / 100.0 for pc in BC_ZONES]
