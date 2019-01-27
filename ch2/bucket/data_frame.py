
import numpy as np
import pandas as pd
from bokeh.models import Range1d


def add_interpolation(name, df, deflt_name, delta=10):
    deflt = df[deflt_name]
    if len(clean(deflt)):
        df[name] = df[deflt_name]
        return df
    else:
        start, finish = df.index[0], df.index[-1]
        even = pd.DataFrame(index=pd.date_range(start, finish, freq=pd.Timedelta(seconds=delta)))
        # now we need to combine without duplicating indices...
        even[name] = 1  # set to 1 on indices we want to interpolate on
        df[name] = np.nan  # add empty to original frame
        df.loc[df.index.isin(even.index), name] = 1  # set to 1 on indices we want to interpolate on
        even = even.loc[~even.index.isin(df.index)]  # drop duplicates
        if len(even):
            df2 = pd.concat([df, even], sort=False)
            df2 = df2.sort_index()
            return df2
        else:
            return df


def interpolate_to(df, name):
    df2 = df.copy()
    df2['keep'] = pd.notna(df2[name])
    df2.interpolate(method='time', inplace=True)
    df2 = df2.loc[df2['keep'] == True]
    return df2


def interpolate_to_index(reference, raw, method='linear'):
    reference = pd.DataFrame(True, index=reference.index, columns=['keep'])
    raw = pd.DataFrame(raw, index=raw.index)
    both = reference.merge(raw, how='outer', left_index=True, right_index=True)
    both.loc[pd.isna(both['keep']), ['keep']] = False
    both.interpolate(method=method, inplace=True)
    both = both.loc[both['keep'] == True]
    return both.drop(columns=['keep']).dropna().iloc[:, 0]


def closed_patch(y, zero=0):
    y = y.dropna()
    x = y.index
    return y.append(pd.Series([zero, zero], index=[x[len(x)-1], x[0]]))


def _delta(z):
    if len(z.dropna()):
        return closed_patch(z)
    else:
        return None


def delta_patches(y1, y2):
    dy = y1 - y2
    scale = dy.dropna().abs().max() * 1.1
    y1 = _delta(dy.clip(lower=0))
    y2 = _delta(dy.clip(upper=0))
    return y1, y2, Range1d(start=-scale, end=scale)


def clean(series):
    return series[~series.isin([np.nan, np.inf, -np.inf, None])]