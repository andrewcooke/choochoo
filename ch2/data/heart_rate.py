
from math import exp

from ch2.stoats.calculate.heart_rate import BC_ZONES


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
