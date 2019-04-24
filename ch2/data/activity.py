from logging import getLogger

import numpy as np
import pandas as pd

from .frame import present, linear_resample, linear_resample_time, median_dt
from ..stoats.names import TIME, DISTANCE, MIN_KM_TIME, MED_KM_TIME, HR_ZONE, PERCENT_IN_Z, TIME_IN_Z, HEART_RATE, \
    MAX_MED_HR_M, MAX_MED_EP_M, POWER_ESTIMATE, TIMESPAN_ID

log = getLogger(__name__)

MAX_MED_MINUTES = (5, 10, 30, 60, 90, 120, 180)


def round_km():
    yield from range(5, 21, 5)
    yield from range(25, 76, 25)
    yield from range(100, 251, 50)
    yield from range(300, 1001, 100)


def times_for_distance(df, km=None, delta=10):
    stats, km = {}, km or round_km()
    t4d = pd.DataFrame({TIME: df.index}, index=df[DISTANCE])
    t4d = t4d[~t4d.index.duplicated(keep='last')]
    t4d[TIME] = (t4d[TIME] - t4d[TIME].iloc[0]).astype(np.int64) / 1e9
    lt4d = linear_resample(t4d, d=delta)
    for target in km:
        n = target * 1000 / delta
        dlt4d = lt4d.diff(periods=n).dropna()
        if present(dlt4d, TIME):
            stats[MIN_KM_TIME % target] = dlt4d[TIME].min()
            stats[MED_KM_TIME % target] = dlt4d[TIME].median()
    return stats


def hrz_stats(df, zones=None):
    stats, zones = {}, zones or range(7)
    ldf = linear_resample_time(df, with_timespan=True)
    hrz = pd.cut(ldf[HR_ZONE], bins=zones).value_counts()
    dt, total = median_dt(ldf), hrz.sum()
    for interval, count in hrz.iteritems():
        zone = interval.right
        stats[PERCENT_IN_Z % zone] = 100 * count / total
        stats[TIME_IN_Z % zone] = dt * count
    return stats


# todo - regularize names
def max_mean(df, params=((POWER_ESTIMATE, MAX_MED_EP_M),), mins=None, delta=10, zero=0):
    stats, mins = {}, mins or MAX_MED_MINUTES
    ldf = linear_resample_time(df, dt=delta, with_timespan=True, keep_nan=True)
    for name, template in params:
        ldf.loc[ldf[TIMESPAN_ID].isnull(), [name]] = zero
        cumsum = ldf[name].cumsum()
        for target in mins:
            n = target // delta
            diff = cumsum.diff(periods=n).dropna()
            if present(diff, name):
                stats[template % target] = diff.max() / n
    return stats


def max_med(df, params=((HEART_RATE, MAX_MED_HR_M),), mins=None, delta=10, gap=0.01):
    stats, mins = {}, mins or MAX_MED_MINUTES
    ldf_all = linear_resample_time(df, dt=delta, with_timespan=False, add_time=False)
    ldf_all.interpolate('nearest')
    ldf_tstamp = ldf_all.loc[ldf_all[TIMESPAN_ID].isin(df[TIMESPAN_ID].unique())].copy()
    ldf_tstamp['gap'] = ldf_tstamp.index.astype(np.int64) / 1e9
    ldf_tstamp['gap'] = ldf_tstamp['gap'].diff()
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
    return stats


if __name__ == '__main__':
    from ch2.data import *
    date = '2017-02-07 07:18:50'
    s = session('-v5')
    df = activity_statistics(s, HEART_RATE, local_time=date, activity_group_name='Bike', with_timespan=True)
    print(max_med(df))
