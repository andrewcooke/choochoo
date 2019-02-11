
import pandas as pd
from bokeh.models import Range1d, PanTool, ZoomInTool, ResetTool, ZoomOutTool, HoverTool
from bokeh.plotting import figure

from .names import DISTANCE_KM, ELEVATION_M
from ...stoats.names import TIMESPAN_ID, CLIMB_DISTANCE, CLIMB_ELEVATION, LOCAL_TIME


def make_tools(y):

    def tooltip(name):
        return name, '@{%s}' % name

    tools = [PanTool(dimensions='width'),
             ZoomInTool(dimensions='width'), ZoomOutTool(dimensions='width'),
             ResetTool(),
             HoverTool(tooltips=[tooltip(x) for x in (y, DISTANCE_KM, LOCAL_TIME)])]
    return tools


def subtract(a, c, key, col):
    cols = [key, col]
    limit = min(a[key].max(), c[key].max())
    a = a.loc[a[key] <= limit, cols]
    c = c.loc[c[key] <= limit, cols]
    both = a.merge(c, how='outer', on=key, sort=True, suffixes=('_a', '_c'))
    both.interpolate(inplace=True, limit_direction='both')
    return pd.DataFrame({col: both[col+'_a'] - both[col+'_c'], key: both[key]})


def patches(x, y, diff):
    y = diff.set_index(x)[y]
    range = y.abs().max() * 1.1
    green = y.clip(lower=0).append(pd.Series([0, 0], index=[y.index[len(y)-1], y.index[0]]))
    red = y.clip(upper=0).append(pd.Series([0, 0], index=[y.index[len(y)-1], y.index[0]]))
    return green, red, Range1d(start=-range, end=range)


def y_range(f, y, source, lo=None, hi=None):
    ylo, yhi = source[y].dropna().min() if lo is None else lo, source[y].dropna().max() if hi is None else hi
    dy = yhi - ylo
    f.y_range = Range1d(start=ylo - 0.1 * dy, end=yhi + 0.1 * dy)


def add_tsid_line(f, x, y, source, color='black'):
    for _, s in source.groupby(TIMESPAN_ID):
        f.line(x=x, y=y, source=s, line_color=color)


def multi_line_plot(nx, ny, x, y, source, other=None, lo=None, hi=None, x_range=None):
    f = figure(plot_width=nx, plot_height=ny, tools=make_tools(y))
    y_range(f, y, source, lo=lo, hi=hi)
    add_tsid_line(f, x, y, source)
    if other is not None:
        add_tsid_line(f, x, y, other, color='grey')
        diff = subtract(source, other, x, y)
        green, red, y_range2 = patches(x, y, diff)
        f.extra_y_ranges = {'delta': y_range2}
        f.patch(x=green.index, y=green, color='green', alpha=0.1, y_range_name='delta')
        f.patch(x=red.index, y=red, color='red', alpha=0.1, y_range_name='delta')
    f.yaxis.axis_label = y
    f.xaxis.axis_label = x
    f.toolbar.logo = None
    if x_range: f.x_range = x_range
    return f


def add_cum_line(f, y, source, color='black'):
    y_c = source[y].sort_values(ascending=False).reset_index(drop=True)
    f.line(x=y_c.index, y=y_c, line_color=color)
    f.x_range = Range1d(start=y_c.index.max(), end=y_c.index.min())
    df = y_c.to_frame('y')
    df['x'] = df.index
    return df


def cumulative_plot(nx, ny, y, source, other=None, lo=None, hi=None):
    f = figure(plot_width=nx, plot_height=ny, y_axis_location='right')
    y_range(f, y, source, lo=lo, hi=hi)
    y1 = add_cum_line(f, y, source)
    if other is not None:
        y2 = add_cum_line(f, y, other, color='grey')
        diff = subtract(y1, y2, 'x', 'y')
        green, red, y_range2 = patches('x', 'y', diff)
        f.extra_y_ranges = {'delta': y_range2}
        f.patch(x=green.index, y=green, color='green', alpha=0.1, y_range_name='delta')
        f.patch(x=red.index, y=red, color='red', alpha=0.1, y_range_name='delta')
    f.xaxis.visible = False
    f.yaxis.axis_label = y
    f.toolbar_location = None
    return f


def add_climbs(f, climbs, source):
    for time, climb in climbs.iterrows():
        i = source.index.get_loc(time, method='nearest')
        x = source[DISTANCE_KM].iloc[i]
        x = (x - climb[CLIMB_DISTANCE] / 1000, x)
        y = source[ELEVATION_M].iloc[i]
        y = (y - climb[CLIMB_ELEVATION], y)
        f.line(x=x, y=y, color='red', line_width=5, alpha=0.2)
        for xx, yy in zip(x, y):
            f.circle(x=xx, y=yy, color='red', size=8, alpha=0.2)
