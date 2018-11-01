
ACTIVE_DISTANCE = 'Active Distance'
ACTIVE_TIME = 'Active Time'
ACTIVE_SPEED = 'Active Speed'
FTHR = 'FTHR'
MEDIAN_KM_TIME = 'Median %dkm Time'
MEDIAN_KM_TIME_ANY = 'Median % Time'
PERCENT_IN_Z = 'Percent in Z%d'
PERCENT_IN_Z_ANY = 'Percent in Z%'
TIME_IN_Z = 'Time in Z%d'
MAX_MED_HR_M = 'Max Med HR %dm'
MAX_MED_HR_M_ANY = 'Max Med HR %'
HR_MINUTES = (5, 10, 15, 20, 30, 60, 90, 120, 180)

MAX = '[max]'
MIN = '[min]'

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


STEPS = 'Steps'
REST_HR = 'Rest HR'