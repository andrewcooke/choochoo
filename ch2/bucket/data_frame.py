
import pandas as pd
from bokeh.models import Range1d


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
    both['keep'].loc[pd.isna(both['keep'])] = False
    both.interpolate(method=method, inplace=True)
    both = both.loc[both['keep'] == True]
    return both.drop(columns=['keep']).dropna().iloc[:, 0]


def closed_patch(y, zero=0):
    x = y.index
    return y.append(pd.Series([zero, zero], index=[x[len(x)-1], x[0]]))


def _delta(z):
    z = z.dropna()
    if len(z):
        return closed_patch(z)
    else:
        return None


def delta_patches(y1, y2):
    dy = y1 - y2
    scale = dy.dropna().abs().max() * 1.1
    y1 = _delta(dy.clip(lower=0))
    y2 = _delta(dy.clip(upper=0))
    return y1, y2, Range1d(start=-scale, end=scale)
