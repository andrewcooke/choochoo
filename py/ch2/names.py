import re
from re import sub

SPACE = '-'  # we don't use _ because sqlite uses that as a wildcard in 'like'
POW_M1 = '\u207b\u00b9'
POW_2 = '\u00b2'
MED_WINDOW = '60s'


class Units:

    BPM = 'bpm'
    D = 'd'
    DEG = 'deg'
    FF = 'FF'
    H = 'h'
    J = 'J'
    KJ = 'kJ'
    KCAL = 'kCal'
    KG = 'kg'
    KM = 'km'
    KMH = f'kmh{POW_M1}'
    M = 'm'
    MS = f'ms{POW_M1}'
    PC = '%'
    RPM = 'rpm'
    S = 's'
    STEPS_UNITS = 'stp'
    W = 'W'


class TitlesBase:

    @staticmethod
    def _cov(name): return f'Cov {name}'  # coverage

    @staticmethod
    def _delta(name): return f'Δ {name}'

    @staticmethod
    def _avg(name): return f'Avg {name}'

    @staticmethod
    def _slash(name, units): return f'{name} / {units}'

    @staticmethod
    def _log(name): return f'Log {name}'

    @staticmethod
    def _sqr(name): return f'{name}{POW_2}'

    @staticmethod
    def _new(name): return f'New {name}'

    @staticmethod
    def _src(name): return f'Src {name}'

    @staticmethod
    def _lo(name): return f'Lo {name}'

    @staticmethod
    def _hi(name): return f'Hi {name}'

    @staticmethod
    def _s(name): return f'{name}s'

    @staticmethod
    def _med(name): return f'Med{MED_WINDOW} {name}'


class Titles(TitlesBase):

    AGE = 'Age'
    ACTIVE_DISTANCE = 'Active Distance'
    ACTIVE_SPEED = 'Active Speed'
    ACTIVE_TIME = 'Active Time'
    ACTIVITY = 'Activity'
    ACTIVITY_GROUP = 'Activity Group'
    ALL = 'All'
    ANY_ALL = '% All'
    ALTITUDE = 'Altitude'
    ASPECT_RATIO = 'Aspect Ratio'
    BOOKMARK = 'Bookmark'
    CADENCE = 'Cadence'
    CALORIE_ESTIMATE = 'Calorie Estimate'
    CDA = 'CdA'
    CLIMB = 'Climb'
    CLIMB_ANY = 'Climb %'
    CLIMB_CATEGORY = 'Climb Category'
    CLIMB_DISTANCE = 'Climb Distance'
    CLIMB_ELEVATION = 'Climb Elevation'
    CLIMB_GRADIENT = 'Climb Gradient'
    CLIMB_TIME = 'Climb Time'
    CLIMB_POWER = 'Climb Power'
    COLOR = 'Color'
    COVERAGE = 'Coverage'
    CRR = 'Crr'
    CUMULATIVE_STEPS = 'Cumulative Steps'
    CUMULATIVE_STEPS_START = 'Cumulative Steps Start'
    CUMULATIVE_STEPS_FINISH = 'Cumulative Steps Finish'
    DAILY_STEPS = 'Daily Steps'
    DEFAULT = 'Default'
    DEFAULT_ANY = 'Default %'
    DELAYED_POWER = 'Delayed Power'
    DETRENDED_HEART_RATE = 'Detrended Heart Rate'
    DIRECTION = 'Direction'
    DISTANCE = 'Distance'
    DISTANCE_TIME = 'Distance & Time'
    EARNED_D = 'Earned %d'
    EARNED_D_ANY= 'Earned %'
    ELAPSED_TIME = 'Elapsed Time'
    ELEVATION = 'Elevation'
    ENERGY = 'Energy'
    ENERGY_ESTIMATE = 'Energy Estimate'
    FATIGUE = 'Fatigue'
    FINISH = 'Finish'
    FITNESS = 'Fitness'
    FATIGUE_D = 'Fatigue %dd'
    FATIGUE_ANY = 'Fatigue %'
    ANY_FATIGUE_ANY = '% Fatigue %'
    FITNESS_D = 'Fitness %dd'
    FITNESS_ANY = 'Fitness %'
    ANY_FITNESS_ANY = '% Fitness %'
    FTHR = 'FTHR'
    GRADE = 'Grade'
    GROUP = 'Group'
    HEADING = 'Heading'
    HEART_RATE = 'Heart Rate'
    HR_IMPULSE_10 = 'HR Impulse / 10s'
    HR_ZONE = 'HR Zone'
    INDEX = 'Index'
    KIT = 'Kit'
    KIT_ADDED = 'Kit Added'
    KIT_RETIRED = 'Kit Retired'
    KIT_USED = 'Kit Used'
    LATITUDE = 'Latitude'
    LIFETIME = 'Lifetime'
    LOCAL_TIME = 'Date'
    LONGITUDE = 'Longitude'
    LON_LAT = 'Lon / Lat'
    LOSS = 'Loss'
    MAX_MEAN_PE_M = 'Max Mean PE %dm'
    MAX_MEAN_PE_M_ANY = 'Max Mean PE %'
    MAX_MED_HR_M = 'Max Med HR %dm'
    MAX_MED_HR_M_ANY = 'Max Med HR %'
    MEAN_POWER_ESTIMATE = 'Mean Power Estimate'
    MED_KM_TIME = 'Med %dkm Time'
    MED_KM_TIME_ANY = 'Med % Time'
    MIN_KM_TIME = 'Min %dkm Time'
    MIN_KM_TIME_ANY = 'Min % Time'
    MIXED = 'Mixed'
    NAME = 'Name'
    PERCENT_IN_Z = 'Percent in Z%d'
    PERCENT_IN_Z_ANY = 'Percent in Z%'
    POINTS = 'Points'
    PLATEAU_D = 'Plateau %d'
    PLATEAU_D_ANY = 'Plateau %'
    POWER_ESTIMATE = 'Power Estimate'
    PREDICTED_HEART_RATE = 'Predicted Heart Rate'
    RESPONSES = 'Responses'
    RECOVERY_D = 'Recovery %d'
    RECOVERY_D_ANY = 'Recovery %'
    SECTOR_TIME = 'Sector Time'
    SECTOR_DISTANCE = 'Sector Distance'
    SEGMENT_TIME = 'Segment Time'
    SEGMENT_DISTANCE = 'Segment Distance'
    SEGMENT_HEART_RATE = 'Segment Heart Rate'
    SOURCE = 'Source'
    SPEED = 'Speed'
    SPHERICAL_MERCATOR_X = 'Spherical Mercator X'
    SPHERICAL_MERCATOR_Y = 'Spherical Mercator Y'
    START = 'Start'
    STEPS = 'Steps'
    RAW_ELEVATION = 'Raw Elevation'
    REST_HR = 'Rest HR'
    TIME = 'Time'
    TIME_IN_Z = 'Time in Z%d'
    TIME_IN_Z_ANY = 'Time in Z%'
    TIMESPAN_ID = 'Timespan ID'
    TOTAL_CLIMB = 'Total Climb'

    LO_REST_HR = TitlesBase._lo(REST_HR)
    HI_REST_HR = TitlesBase._hi(REST_HR)

    SPEED_2 = TitlesBase._sqr(SPEED)
    AVG_SPEED_2 = TitlesBase._avg(SPEED_2)
    DELTA_SPEED_2 = TitlesBase._delta(SPEED_2)

    DELTA_TIME = TitlesBase._delta(TIME)
    DELTA_DISTANCE = TitlesBase._delta(DISTANCE)
    DELTA_ELEVATION = TitlesBase._delta(ELEVATION)
    DELTA_SPEED = TitlesBase._delta(SPEED)
    DELTA_ENERGY = TitlesBase._delta(ENERGY)

    ACTIVE_DISTANCE_KM = TitlesBase._slash(ACTIVE_DISTANCE, Units.KM)
    ACTIVE_TIME_H = TitlesBase._slash(ACTIVE_TIME, Units.H)
    ACTIVE_TIME_S = TitlesBase._slash(ACTIVE_TIME, Units.S)
    CADENCE_RPM = TitlesBase._slash(CADENCE, Units.RPM)
    CLIMB_MS = TitlesBase._slash(CLIMB, Units.MS)
    DISTANCE_KM = TitlesBase._slash(DISTANCE, Units.KM)
    ELEVATION_M = TitlesBase._slash(ELEVATION, Units.M)
    GRADE_PC = TitlesBase._slash(GRADE, Units.PC)
    HEART_RATE_BPM = TitlesBase._slash(HEART_RATE, Units.BPM)
    REST_HR_BPM = TitlesBase._slash(REST_HR, Units.BPM)
    SPEED_KMH = TitlesBase._slash(SPEED, Units.KMH)
    SPEED_MS = TitlesBase._slash(SPEED, Units.MS)
    POWER_ESTIMATE_W = TitlesBase._slash(POWER_ESTIMATE, Units.W)

    MED_SPEED_KMH = TitlesBase._med(SPEED_KMH)
    MED_HEART_RATE_BPM = TitlesBase._med(HEART_RATE_BPM)
    MED_HR_IMPULSE_10 = TitlesBase._med(HR_IMPULSE_10)
    MED_CADENCE_RPM = TitlesBase._med(CADENCE_RPM)
    MED_POWER_ESTIMATE_W = TitlesBase._med(POWER_ESTIMATE_W)

    POWER_HR = 'Power / HR'
    POWER_HR_LAG = 'Power / HR Lag'
    HR_DRIFT = 'HR Drift'
    LOG_HR_DRIFT = TitlesBase._log('HR Drift')
    IDLE_HR = 'Idle HR'
    WIND_SPEED = 'Wind Speed'
    WIND_HEADING = 'Wind Heading'


class Sports:

    SPORT_MAP = 'SportMap'
    SPORT_CYCLING = 'cycling'
    SPORT_RUNNING = 'running'
    SPORT_SWIMMING = 'swimming'
    SPORT_WALKING = 'walking'
    SPORT_GENERIC = 'generic'


class Summaries:

    MAX = 'max'
    MIN = 'min'
    CNT = 'cnt'
    AVG = 'avg'
    SUM = 'sum'
    MSR = 'msr'   # measure (separate table, less efficient)

    @staticmethod
    def join(*args): return ','.join(args)


def any_to_fmt(pattern, fmt='%s'):
    return pattern.replace('%', fmt)


def like(pattern, names):
    return list(_like(pattern, names))


def _like(pattern, names, test=True):
    matcher = re.compile(pattern.replace('%', '.+'))
    for name in names:
        if bool(matcher.match(name)) == test:
            yield name


def unlike(pattern, names):
    return list(_like(pattern, names, test=False))


def titles_for_names(title_pattern, names):
    title_left, title_right = title_pattern.split('%')
    name_left, name_right = simple_name(title_pattern).split('%')
    pattern = re.compile(f'{name_left}(.+){name_right}')
    for name in names:
        match = pattern.match(name)
        if match:
            yield title_left + match.group(1) + title_right


class NamesMeta(type):

    def __getattribute__(cls, item):
        value = type.__getattribute__(cls, item)
        if item[0].isalpha() and item[0].upper() == item[0]:
            return simple_name(value)
        elif len(item) > 1 and item[0] == '_' and item[1].isalpha():
            def wrapper(*args):
                return simple_name(value(*args))
            return wrapper
        else:
            return value


class Names(Titles, metaclass=NamesMeta): pass


T, N, U, S = Titles, Names, Units, Summaries


def simple_name(name, none=True, strip=True):
    # allows % and ? for LIKE and templates
    # also allows ':' so that we don't mess up composites
    from ch2.names import POW_2, POW_M1, SPACE
    if name is None and none:
        return None
    name = name.replace(POW_2, '2')
    name = name.replace(POW_M1, '')  # ms^-1 -> ms which is standard convention
    name = name.replace('Δ', 'd ')
    if strip: name = name.strip()
    name = name.lower()
    name = sub(r'\s+', SPACE, name)
    name = sub(r'[^a-z0-9%?:]', SPACE, name)
    name = sub(r'^(\d)', SPACE + r'\1', name)
    name = sub(SPACE + '+', SPACE, name)
    return name
