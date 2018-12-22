
import datetime as dt

import pandas as pd


def col_to_boxstats(frame, name):
    '''
    Allow inter-op with matplotlib using pre-calculated stats
    See test_data.py
    '''
    stats = []
    for index, row in frame.iterrows():
        if row[name]:
            stats.append({'label': index,
                          'whislo': row[name][0],
                          'q1': row[name][1],
                          'med': row[name][2],
                          'q3': row[name][3],
                          'whishi': row[name][4]})
    return stats


def bokeh_boxplot(f, col):
    '''
    Generate a boxplot for a column (pandas series) containing a tuple of 5 values
    (index date) as provided by summary statistics,
    '''
    def pick(n):
        def pick(x):
            return x[n] if x else None
        return pick
    q = [col.map(pick(i)) for i in range(5)]
    f.segment(q[0].index, q[0], q[1].index, q[1])
    f.vbar(q[1].index, dt.timedelta(days=20), q[1], q[2], fill_alpha=0)
    f.vbar(q[2].index, dt.timedelta(days=20), q[2], q[3], fill_alpha=0)
    f.segment(q[3].index, q[3], q[4].index, q[4])


def closed_patch(x, y, zero=0):
    x2 = x.append(pd.Series([x[len(x)-1], x[0]]))
    y2 = y.append(pd.Series([zero, zero]))
    return x2, y2
