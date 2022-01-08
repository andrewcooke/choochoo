
import numpy as np
import pandas as pd

from .heart_rate import BC_ZONES
from ..common.date import to_time
from ..lib.data import interpolate_freq, safe_none, safe_return
from ..names import N


@safe_none
def hr_zone(heart_rate_df, fthr_df, pc_fthr_zones=BC_ZONES, heart_rate=N.HEART_RATE, hr_zone=N.HR_ZONE):
    '''
    mutate input df to include hr zone

    this can be used for a huge slew of data, or for an individual activity.
    '''
    fthrs = sorted([(time, row[N.FTHR]) for time, row in fthr_df.dropna().iterrows()], reverse=True)
    if not fthrs:
        raise Exception(f'No {N.FTHR} defined')
    fthrs = fthrs + [(to_time('2100'), None)]
    fthrs = [(a[0], b[0], a[1]) for a, b in zip(fthrs, fthrs[1:])]
    heart_rate_df[hr_zone] = np.nan
    for start, finish, fthr in fthrs:  # start is inclusive
        start, finish = pd.to_datetime(start, utc=True), pd.to_datetime(finish, utc=True)
        zones = [x * fthr / 100.0 for x in pc_fthr_zones]
        for zone, upper in enumerate(zones + [None]):
            if zone == 0:
                # we don't try to distinguish zones below 1
                heart_rate_df.loc[(heart_rate_df.index >= start) & (heart_rate_df.index < finish) &
                                  (heart_rate_df[heart_rate] <= upper),
                                  [hr_zone]] = zone
            elif not upper:
                # or above 5
                heart_rate_df.loc[(heart_rate_df.index >= start) & (heart_rate_df.index < finish) &
                                  (heart_rate_df[heart_rate] > lower),
                                  [hr_zone]] = zone
            else:
                hrz = ((heart_rate_df.loc[(heart_rate_df.index >= start) & (heart_rate_df.index < finish) &
                                          (heart_rate_df[heart_rate] > lower) & (heart_rate_df[heart_rate] <= upper),
                                          [heart_rate]] - lower) / (upper - lower)) + zone
                # .values below from
                # https://stackoverflow.com/questions/12307099/modifying-a-subset-of-rows-in-a-pandas-dataframe
                # i do not understand why it is needed...
                heart_rate_df.loc[(heart_rate_df.index >= start) & (heart_rate_df.index < finish) &
                                  (heart_rate_df[heart_rate] > lower) & (heart_rate_df[heart_rate] <= upper),
                                  [hr_zone]] = hrz.values
            lower = upper


@safe_return(lambda: pd.DataFrame(columns=[N.HR_IMPULSE_10]))
def impulse_10(hr_zone_df, impulse, hr_zone=N.HR_ZONE):
    '''
    interpolate HR to 10s values then calculate impulse using model parameters.

    this can be used for a huge slew of data, or for an individual activity.
    '''
    impulse_df = interpolate_freq(hr_zone_df.loc[:, [hr_zone]], '10s',
                                  method='index', limit=int(0.5 + impulse.max_secs / 10)).dropna()
    impulse_df[N.HR_IMPULSE_10] = (impulse_df[hr_zone] - impulse.zero) / (impulse.one - impulse.zero)
    impulse_df[N.HR_IMPULSE_10].clip(lower=0, inplace=True)
    impulse_df[N.HR_IMPULSE_10] = impulse_df[N.HR_IMPULSE_10] ** impulse.gamma
    impulse_df.drop(columns=[hr_zone], inplace=True)
    return impulse_df
