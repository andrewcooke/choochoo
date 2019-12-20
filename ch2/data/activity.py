
from logging import getLogger

import numpy as np
import pandas as pd
from math import atan2, cos, sin, sqrt, pi

from .frame import linear_resample, median_dt, present, linear_resample_time
from ..lib.log import log_current_exception
from ..stats.names import HEART_RATE, MAX_MED_HR_M, POWER_ESTIMATE, ACTIVE_DISTANCE, ACTIVE_TIME, \
    ACTIVE_SPEED, TIMESPAN_ID, TIME, DISTANCE, MIN_KM_TIME, MED_KM_TIME, PERCENT_IN_Z, TIME_IN_Z, HR_ZONE, \
    MAX_MEAN_PE_M, SPHERICAL_MERCATOR_X, SPHERICAL_MERCATOR_Y, DIRECTION, ASPECT_RATIO

log = getLogger(__name__)

MAX_MINUTES = (5, 10, 30, 60, 90, 120, 180)


def round_km():
    yield from range(5, 21, 5)
    yield from range(25, 76, 25)
    yield from range(100, 251, 50)
    yield from range(300, 1001, 100)


def active_stats(df):
    stats = {ACTIVE_DISTANCE: 0, ACTIVE_TIME: 0, ACTIVE_SPEED: 0}
    for timespan in df[TIMESPAN_ID].dropna().unique():
        slice = df.loc[df[TIMESPAN_ID] == timespan]
        stats[ACTIVE_DISTANCE] += slice[DISTANCE].max() - slice[DISTANCE].min()
        stats[ACTIVE_TIME] += (slice.index.max() - slice.index.min()).total_seconds()
    stats[ACTIVE_SPEED] = 3.6 * stats[ACTIVE_DISTANCE] / stats[ACTIVE_TIME]
    return stats


def times_for_distance(df, km=None, delta=10):
    stats, km = {}, km or round_km()
    try:
        tmp = pd.DataFrame({TIME: df.index}, index=df[DISTANCE])
        tmp = tmp[~tmp.index.duplicated(keep='last')]
        t4d = pd.DataFrame({TIME: (tmp[TIME] - tmp[TIME].iloc[0]).astype(np.int64) / 1e9}, index=df[DISTANCE])
        lt4d = linear_resample(t4d, d=delta)
        for target in km:
            n = target * 1000 / delta
            dlt4d = lt4d.diff(periods=n).dropna()
            if present(dlt4d, TIME):
                stats[MIN_KM_TIME % target] = dlt4d[TIME].min()
                stats[MED_KM_TIME % target] = dlt4d[TIME].median()
    except Exception as e:
        log.warning(f'No Time for Distance stats: {e}')
    return stats


def hrz_stats(df, zones=None):
    stats, zones = {}, zones or range(1, 8)
    try:
        if present(df, HR_ZONE):
            ldf = linear_resample_time(df, with_timespan=True)
            hrz = pd.cut(ldf[HR_ZONE], bins=zones, right=False).value_counts()
            dt, total = median_dt(ldf), hrz.sum()
            for interval, count in hrz.iteritems():
                zone = interval.left
                stats[PERCENT_IN_Z % zone] = 100 * count / total
                stats[TIME_IN_Z % zone] = dt * count
    except Exception as e:
        log.warning(f'No HR stats: {e}')
    return stats


def max_mean_stats(df, params=((POWER_ESTIMATE, MAX_MEAN_PE_M),), mins=None, delta=10, zero=0):
    stats, mins = {}, mins or MAX_MINUTES
    try:
        ldf = linear_resample_time(df, dt=delta, with_timespan=True, keep_nan=True)
        for name, template in params:
            if name in ldf.columns:
                ldf.loc[ldf[TIMESPAN_ID].isnull(), [name]] = zero
                cumsum = ldf[name].cumsum()
                for target in mins:
                    n = (target * 60) // delta
                    diff = cumsum.diff(periods=n).dropna()
                    if present(diff, name):
                        stats[template % target] = diff.max() / n
            else:
                log.warning(f'Missing {name}')
    except Exception as e:
        log.warning(f'No Max Mean stats: {e}')
        log_current_exception()
    return stats


def max_med_stats(df, params=((HEART_RATE, MAX_MED_HR_M),), mins=None, delta=10, gap=0.01):
    stats, mins = {}, mins or MAX_MINUTES
    try:
        ldf_all = linear_resample_time(df, dt=delta, with_timespan=False, add_time=False)
        ldf_all.interpolate('nearest')
        ldf_tstamp = ldf_all.loc[ldf_all[TIMESPAN_ID].isin(df[TIMESPAN_ID].unique())].copy()
        ldf_tstamp.loc[:, 'gap'] = ldf_tstamp.index.astype(np.int64) / 1e9
        ldf_tstamp.loc[:, 'gap'] = ldf_tstamp['gap'].diff()
        log.debug(f'Largest gap is {ldf_tstamp["gap"].max()}s')
        for target in mins:
            n = target * 60 // delta
            log.debug(f'Target {target}m is {n} samples (delta {delta}s)')
            splits, remain = [], ldf_all.copy()
            max_gap = max(gap * target * 60, 1.5 * delta)
            for after in ldf_tstamp.index[ldf_tstamp['gap'] > max_gap].tolist():
                before = ldf_tstamp.index[ldf_tstamp.index.get_loc(after)-1]
                splits.append(remain.loc[:before])
                remain = remain.loc[after:]
            splits.append(remain)
            log.debug(f'Split data into {len(splits)} sections for {target}m with max gap of {max_gap}s')
            for name, template in params:
                stat_name = template % target
                for split in splits:
                    split['med'] = split[name].rolling(n).median()
                    if present(split, 'med'):
                        max_med = split['med'].dropna().max()
                        if stat_name in stats:
                            stats[stat_name] = max(stats[stat_name], max_med)
                        else:
                            stats[stat_name] = max_med
    except Exception as e:
        log.warning(f'No Max Med stats: {e}')
        log_current_exception()
    return stats


def direction_stats(df):
    stats = {}
    try:
        if all(name in df.columns for name in (SPHERICAL_MERCATOR_X, SPHERICAL_MERCATOR_Y)):
            df = df.dropna(subset=[SPHERICAL_MERCATOR_X, SPHERICAL_MERCATOR_Y]).copy()
            if not df.empty:
                x0, y0 = df.iloc[0][SPHERICAL_MERCATOR_X], df.iloc[0][SPHERICAL_MERCATOR_Y]
                df.loc[:, 'dx'] = df[SPHERICAL_MERCATOR_X] - x0
                df.loc[:, 'dy'] = df[SPHERICAL_MERCATOR_Y] - y0
                # average position
                dx, dy = df['dx'].mean(), df['dy'].mean()
                x1, y1, d = x0 + dx, y0 + dy, sqrt(dx ** 2 + dy ** 2)
                theta = atan2(dy, dx)
                # change coords to centred on average position and perp / parallel to line to start
                df.loc[:, 'dx'] = df[SPHERICAL_MERCATOR_X] - x1
                df.loc[:, 'dy'] = df[SPHERICAL_MERCATOR_Y] - y1
                df.loc[:, 'u'] = df['dx'] * cos(theta) + df['dy'] * sin(theta)
                df.loc[:, 'v'] = df['dy'] * cos(theta) - df['dx'] * sin(theta)
                # convert from angle anti-clock from x axis to bearing
                stats[DIRECTION] = 90 - 180 * theta / pi
                stats[ASPECT_RATIO] = df['v'].std() / df['u'].std()
    except Exception as e:
        log.warning(f'No Direction stats: {e}')
    return stats


# if __name__ == '__main__':
#     from . import *
#     date = '2017-02-07 07:18:50'
#     s = session('-v5')
#     df = activity_statistics(s, SPHERICAL_MERCATOR_X, SPHERICAL_MERCATOR_Y,
#                              local_time=date, activity_group_name='Bike', with_timespan=True)
#     print(direction_stats(df))
