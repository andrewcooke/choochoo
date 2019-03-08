
import numpy as np
import pandas as pd

from ..stoats.names import *


def median_freq(stats):
    return pd.Series(stats.index).diff().median()


def linear_resample(stats, start=None, finish=None, freq=None, with_timestamp=None, keep_nan=True):
    if with_timestamp is None: with_timestamp = TIMESPAN_ID in stats.columns
    freq = freq or median_freq(stats)
    start = start or stats.index.min()
    finish = finish or stats.index.max()
    even = pd.DataFrame({'keep': True}, index=pd.date_range(start=start, end=finish, freq=freq))
    both = stats.join(even, how='outer', sort=True)
    both.loc[both['keep'] != True, ['keep']] = False  # not sure this is needed, but avoid interpolating to true
    both.interpolate(method='index', limit_area='inside', inplace=True)
    resampled = both.loc[both['keep'] == True].drop(columns=['keep'])
    resampled[TIME] = resampled.index
    resampled[DELTA_TIME] = resampled[TIME].diff()
    if with_timestamp:
        if keep_nan:
            resampled.loc[~resampled[TIMESPAN_ID].isin(stats[TIMESPAN_ID].unique())] = np.nan
        else:
            resampled = resampled.loc[resampled[TIMESPAN_ID].isin(stats[TIMESPAN_ID].unique())]
    return freq, resampled
