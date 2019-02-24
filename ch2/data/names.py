
from ch2.stoats.names import DISTANCE, SPEED, ELEVATION, HR_IMPULSE_10, CADENCE, FITNESS, FATIGUE, ACTIVE_DISTANCE, \
    ACTIVE_TIME

# additional names not used within the database, but used for display by the notetbook
# (bokeh is easiest if dataframe columns are also labels).

WINDOW = '60s'
POW_MINUS_ONE = '\u207b\u00b9'
POW_TWO = '\u00b2'
MIN_PERIODS = 1

DISTANCE_KM = '%s / km' % DISTANCE
SPEED_KMH = '%s / kmh%s' % (SPEED, POW_MINUS_ONE)
MED_SPEED_KMH = 'M(%s) %s / kmh%s' % (WINDOW, SPEED, POW_MINUS_ONE)
ELEVATION_M = '%s / m' % ELEVATION
CLIMB_MS = 'Climb / ms%s' % POW_MINUS_ONE
MED_HR_IMPULSE_10 = 'M(%s) %s' % (WINDOW, HR_IMPULSE_10)
MED_CADENCE = 'M(%s) %s' % (WINDOW, CADENCE)
LOG_FITNESS = 'Log %s' % FITNESS
LOG_FATIGUE = 'Log %s' % FATIGUE
ACTIVE_DISTANCE_KM = '%s / km' % ACTIVE_DISTANCE
ACTIVE_TIME_H = '%s / h' % ACTIVE_TIME
