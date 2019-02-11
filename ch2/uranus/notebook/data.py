
import pandas as pd

from .names import DISTANCE_KM, SPEED_KMH, MED_SPEED_KMH, MED_HR_IMPULSE_10, WINDOW, MIN_PERIODS, \
    ELEVATION_M, CLIMB_MS
from ...data import activity_statistics
from ...lib.date import time_to_local_time, to_time
from ...stoats.names import LATITUDE, LONGITUDE, SPHERICAL_MERCATOR_X, SPHERICAL_MERCATOR_Y, DISTANCE, CADENCE, \
    ALTITUDE, HR_IMPULSE_10, HR_ZONE, SPEED, ELEVATION, TIME, LOCAL_TIME


def std_stats(s, date):

    stats = activity_statistics(s, LATITUDE, LONGITUDE, SPHERICAL_MERCATOR_X, SPHERICAL_MERCATOR_Y, DISTANCE,
                                ELEVATION, SPEED, HR_ZONE, HR_IMPULSE_10, ALTITUDE, CADENCE,
                                time=date, with_timespan=True)

    stats[DISTANCE_KM] = stats[DISTANCE]/1000
    stats[SPEED_KMH] = stats[SPEED] * 3.6
    stats[MED_SPEED_KMH] = stats[SPEED].rolling(WINDOW, min_periods=MIN_PERIODS).median() * 3.6
    stats[MED_HR_IMPULSE_10] = stats[HR_IMPULSE_10].rolling(WINDOW, min_periods=MIN_PERIODS).median()
    stats.rename(columns={ELEVATION: ELEVATION_M}, inplace=True)

    stats['keep'] = pd.notna(stats[HR_IMPULSE_10])
    stats.interpolate(method='time', inplace=True)
    stats = stats.loc[stats['keep'] == True]

    stats[CLIMB_MS] = stats[ELEVATION_M].diff() * 0.1
    stats[TIME] = pd.to_datetime(stats.index)
    # stats[LOCAL_TIME] = stats[TIME].apply(lambda x: time_to_local_time(x).strftime('%H:%M:%S'))
    # this seems to be a bug in pandas not supporting astimezone for some weird internal datetime
    stats[LOCAL_TIME] = stats[TIME].apply(lambda x: time_to_local_time(to_time(x.timestamp())).strftime('%H:%M:%S'))

    return stats

