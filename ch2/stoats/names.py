
POW_M1 = '\u207b\u00b9'
POW_2 = '\u00b2'

ACTIVE_DISTANCE = 'Active Distance'
ACTIVE_TIME = 'Active Time'
ACTIVE_SPEED = 'Active Speed'
ACTIVITY = 'Activity'
AIR_SPEED = 'Air Speed'
ALTITUDE = 'Altitude'
CADENCE = 'Cadence'
CDA = 'CdA'
CLIMB = 'Climb'
CLIMB_DISTANCE = 'Climb Distance'
CLIMB_ELEVATION = 'Climb Elevation'
CLIMB_GRADIENT = 'Climb Gradient'
CLIMB_TIME = 'Climb Time'
CRR = 'Crr'
CUMULATIVE_STEPS_START = 'Cumulative Steps Start'
CUMULATIVE_STEPS_FINISH = 'Cumulative Steps Finish'
DAILY_STEPS = 'Daily Steps'
DISTANCE = 'Distance'
ELEVATION = 'Elevation'
ENERGY = 'Energy'
FATIGUE = 'Fatigue'
FITNESS = 'Fitness'
FTHR = 'FTHR'
HEADING = 'Heading'
HEART_RATE = 'Heart Rate'
HR_IMPULSE = 'HR Impulse'
HR_IMPULSE_10 = 'HR Impulse / 10s'
HR_ZONE = 'HR Zone'
LATITUDE = 'Latitude'
LOCAL_TIME = 'Date'
LONGITUDE = 'Longitude'
LOSS = 'Loss'
MAX_MED_HR_M = 'Max Med HR %dm'
MAX_MED_HR_M_ANY = 'Max Med HR %'
MEDIAN_KM_TIME = 'Median %dkm Time'
MEDIAN_KM_TIME_ANY = 'Median % Time'
PERCENT_IN_Z = 'Percent in Z%d'
PERCENT_IN_Z_ANY = 'Percent in Z%'
POWER = 'Power'
SEGMENT_TIME = 'Segment Time'
SEGMENT_DISTANCE = 'Segment Distance'
SEGMENT_HEART_RATE = 'Segment Heart Rate'
SPEED = 'Speed'
SPHERICAL_MERCATOR_X = 'Spherical Mercator X'
SPHERICAL_MERCATOR_Y = 'Spherical Mercator Y'
STEPS = 'Steps'
RAW_ELEVATION = 'Raw Elevation'
REST_HR = 'Rest HR'
TIME = 'Time'
TIME_IN_Z = 'Time in Z%d'
TIMESPAN_ID = 'Timespan ID'
TOTAL_CLIMB = 'Total Climb'


MAX = '[max]'
MIN = '[min]'
CNT = '[cnt]'
AVG = '[avg]'
SUM = '[sum]'
MSR = '[msr]'   # measure (separate table, less efficient)
def summaries(*args): return ','.join(args)


BPM = 'bpm'
DEG = 'deg'
ENTRIES = 'entries'
H = 'h'
J = 'J'
KG = 'kg'
KM = 'km'
KMH = f'kmh{POW_M1}'
M = 'm'
MS = f'ms{POW_M1}'
PC = '%'
RPM = 'rpm'
S = 's'
STEPS_UNITS = 'steps'
W = 'W'


def _d(name): return f'Delta {name}'
def _avg(name): return f'Avg {name}'
def _cor(name): return f'Cor {name}'
def _slash(name, units): return f'{name} / {units}'
def _log(name): return f'Log {name}'
def _sqr(name): return f'{name}{POW_2}'

MED_WINDOW = '60s'
def _med(name): return f'Med{MED_WINDOW} {name}'


AIR_SPEED_2 = _sqr(AIR_SPEED)
AVG_AIR_SPEED_2 = _avg(AIR_SPEED_2)
DELTA_AIR_SPEED_2 = _d(AIR_SPEED_2)

SPEED_2 = _sqr(SPEED)
AVG_SPEED_2 = _avg(SPEED_2)
DELTA_SPEED_2 = _d(SPEED_2)

DELTA_TIME = _d(TIME)
DELTA_DISTANCE = _d(DISTANCE)
DELTA_ELEVATION = _d(ELEVATION)
DELTA_SPEED = _d(SPEED)
DELTA_ENERGY = _d(ENERGY)
COR_HEART_RATE = _cor(HEART_RATE)

ACTIVE_DISTANCE_KM = _slash(ACTIVE_DISTANCE, KM)
ACTIVE_TIME_H = _slash(ACTIVE_TIME, H)
CLIMB_MS = _slash(CLIMB, MS)
DISTANCE_KM = _slash(DISTANCE, KM)
ELEVATION_M = _slash(ELEVATION, M)
SPEED_KMH = _slash(SPEED, KMH)
POWER_W = _slash(POWER, W)

LOG_FITNESS = _log(FITNESS)
LOG_FATIGUE = _log(FATIGUE)
MED_SPEED_KMH = _med(SPEED_KMH)
MED_HR_IMPULSE_10 = _med(HR_IMPULSE_10)
MED_CADENCE = _med(CADENCE)
MED_POWER_W = _med(POWER_W)


POWER_HR = 'Power / HR'
HR_DRIFT = 'HR Drift'
IDLE_HR = 'Idle HR'
LOG_HR_DRIFT = _log(HR_DRIFT)
