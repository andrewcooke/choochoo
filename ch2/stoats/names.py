
ACTIVE_DISTANCE = 'Active Distance'
ACTIVE_TIME = 'Active Time'
ACTIVE_SPEED = 'Active Speed'
FTHR = 'FTHR'
MEDIAN_KM_TIME = 'Median %dkm Time'
PERCENT_IN_Z = 'Percent in Z%d'
TIME_IN_Z = 'Time in Z%d'
MAX_MED_HR_OVER_M = 'Max Med HR over %dm'
HR_MINUTES = (5, 10, 15, 20, 30, 60, 90, 120, 180)

MAX = 'max'
MIN = 'min'

M = 'm'
S = 's'
KMH = 'km/h'
PC = '%'
BPM = 'bpm'


def round_km():
    yield from range(5, 21, 5)
    yield from range(25, 76, 25)
    yield from range(100, 251, 50)
    yield from range(300, 1001, 100)
