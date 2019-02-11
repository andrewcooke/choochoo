
ACTIVE_DISTANCE = 'Active Distance'
ACTIVE_TIME = 'Active Time'
ACTIVE_SPEED = 'Active Speed'
ACTIVITY = 'Activity'
ALTITUDE = 'Altitude'
CADENCE = 'Cadence'
CLIMB_DISTANCE = 'Climb Distance'
CLIMB_ELEVATION = 'Climb Elevation'
CLIMB_GRADIENT = 'Climb Gradient'
CLIMB_TIME = 'Climb Time'
CUMULATIVE_STEPS_START = 'Cumulative Steps Start'
CUMULATIVE_STEPS_FINISH = 'Cumulative Steps Finish'
DAILY_STEPS = 'Daily Steps'
DISTANCE = 'Distance'
ELEVATION = 'Elevation'
FATIGUE = 'Fatigue'
FITNESS = 'Fitness'
FTHR = 'FTHR'
HEART_RATE = 'Heart Rate'
HR_IMPULSE = 'HR Impulse'
HR_IMPULSE_10 = 'HR Impulse / 10s'
HR_ZONE = 'HR Zone'
LATITUDE = 'Latitude'
LOCAL_TIME = 'Date'
LONGITUDE = 'Longitude'
MAX_HR = 'MaxHR'  # no spaces because constant name
MAX_SPEED = 'MaxSpeed'  # no spaces because constant name
MEDIAN_KM_TIME = 'Median %dkm Time'
MEDIAN_KM_TIME_ANY = 'Median % Time'
PERCENT_IN_Z = 'Percent in Z%d'
PERCENT_IN_Z_ANY = 'Percent in Z%'
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
MAX_MED_HR_M = 'Max Med HR %dm'
MAX_MED_HR_M_ANY = 'Max Med HR %'

HR_MINUTES = (5, 10, 15, 20, 30, 60, 90, 120, 180)

MAX = '[max]'
MIN = '[min]'
CNT = '[cnt]'
AVG = '[avg]'
SUM = '[sum]'
MSR = '[msr]'   # measure (separate table, less efficient)


def summaries(*args):
    return ','.join(args)


M = 'm'
S = 's'
H = 'h'
DEG = 'deg'
KMH = 'km/h'
MS = 'm/s'
PC = '%'
BPM = 'bpm'
RPM = 'rpm'
KG = 'kg'
STEPS_UNITS = 'steps'
ENTRIES = 'entries'


def round_km():
    yield from range(5, 21, 5)
    yield from range(25, 76, 25)
    yield from range(100, 251, 50)
    yield from range(300, 1001, 100)
