
from math import exp

from ..squeal import StatisticJournal, Constant
from ..stoats.names import FTHR

# values from british cycling online calculator
# these are upper limits
BC_ZONES = (68, 83, 94, 105, 121, 999)


def zone(hr, fthr, zones=BC_ZONES):
    zones = [x * fthr / 100.0 for x in zones]
    for i in range(len(zones)):
        if hr < zones[i]:
            if i == len(zones) - 1:
                return i + 1 + (hr - zones[i-1]) / (zones[i-1] - zones[i-2])
            elif i:
                return i + 1 + (hr - zones[i-1]) / (zones[i] - zones[i-1])
            else:
                return 2 + (hr - zones[0]) / (zones[1] - zones[0])


def shrimp(hr, gamma, zero, fthr, zones=BC_ZONES):
    hrz = zone(hr, fthr, zones)
    n = len(zones) - 1
    return n * (max(0, hrz - zero) / (n - zero)) ** gamma


def trimp(hr, rest_hr, max_hr, k):
    x = (hr - rest_hr) / (max_hr - rest_hr)
    return x * 0.64 * exp(k * x)


def edwards(hr, max_hr):
    return max(0, int(10 * (1 - (max_hr - hr) / max_hr)) - 4)


def hr_zones_from_database(s, activity_group, time):
    fthr = StatisticJournal.before(s, time, FTHR, Constant, activity_group)
    if fthr:
        return hr_zones(fthr.value)
    else:
        return None


def hr_zones(fthr):
    return [fthr * pc / 100.0 for pc in BC_ZONES]