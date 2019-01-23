
import datetime as dt

import numpy as np
import pandas as pd
from bokeh import palettes, tile_providers
from bokeh.models import NumeralTickFormatter, PrintfTickFormatter, Range1d, LinearAxis, PanTool, ZoomInTool, HoverTool, \
    ZoomOutTool, ResetTool
from bokeh.plotting import figure

from .data_frame import interpolate_to_index, delta_patches, closed_patch
from ..stoats.names import TIME, HR_ZONE, CLIMB_DISTANCE, CLIMB_ELEVATION


def clean(s):
    return s[~s.isin([np.nan, np.inf, -np.inf])]


def clean_all(ss):
    if ss is not None:
        return [clean(s) for s in ss]


def max_all(ss):
    return max(s.max() for s in ss if len(s))


def min_all(ss):
    return min(s.min() for s in ss if len(s))


def tools(x=None, y=None):
    tools = [PanTool(dimensions='width'),
             ZoomInTool(dimensions='width'), ZoomOutTool(dimensions='width'),
             ResetTool()]
    if x and y:
        tools.append(HoverTool(tooltips=[(x, '$x'), (y, '$y')]))
    return tools


def dot_map(n, x1, y1, size, x2=None, y2=None):

    f = figure(plot_width=n, plot_height=n, x_axis_type='mercator', y_axis_type='mercator',
               tools=[PanTool(), ZoomInTool(), ZoomOutTool(), ResetTool()])
    f.toolbar.logo = None

    for x, y, s in zip(x1, y1, size):
        f.circle(x=x, y=y, line_alpha=0, fill_color='red', size=s, fill_alpha=0.03)
        f.line(x=x, y=y, line_color='black')

    if x2 is not None:
        for x, y in zip(x2, y2):
            f.line(x=x, y=y, line_color='grey')

    f.add_tile(tile_providers.STAMEN_TERRAIN, alpha=0.1)
    f.axis.visible = False

    return f


def line_diff_elevation_climbs(nx, ny, y1, y2=None, climbs=None, st=None, y3=None, x_range=None):
    from .diary import DISTANCE_KM, ELEVATION_M
    f = line_diff(nx, ny, DISTANCE_KM, y1, y2=y2, x_range=x_range)
    if y3 is not None:
        for y in y3:
            f.line(x=y.index, y=y, color='black', alpha=0.1, line_width=2)
    if climbs is not None:
        all = pd.concat(st)
        for time, climb in climbs.iterrows():
            i = all.index.get_loc(time, method='nearest')
            x = all[DISTANCE_KM].iloc[i]
            x = (x - climb[CLIMB_DISTANCE] / 1000, x)
            y = all[ELEVATION_M].iloc[i]
            y = (y - climb[CLIMB_ELEVATION], y)
            f.line(x=x, y=y, color='red', line_width=5, alpha=0.2)
            for xx, yy in zip(x, y):
                f.circle(x=xx, y=yy, color='red', size=8, alpha=0.2)
    return f


def line_diff(nx, ny, xlabel, y1, y2=None, x_range=None):

    y1, y2 = clean_all(y1), clean_all(y2)
    is_x_time = any(isinstance(s.index[0], dt.datetime) for s in y1 if len(s))

    f = figure(plot_width=nx, plot_height=ny, x_axis_type='datetime' if is_x_time else 'linear',
               tools=tools(xlabel, y1[0].name))
    f.toolbar.logo = None

    y_min, y_max = min_all(y1), max_all(y1)
    if y2:
        y_min, y_max = min(y_min, min_all(y2)), max(y_max, max_all(y2))
    dy = y_max - y_min

    if is_x_time:
        f.xaxis.axis_label = 'Time'
        f.xaxis[0].formatter = NumeralTickFormatter(format='00:00:00')
        zero = min(y.index.min() for y in y1)
        for y in y1:
            y.index = (y.index - zero).total_seconds()
    else:
        f.xaxis.axis_label = xlabel
        f.xaxis[0].formatter = PrintfTickFormatter(format='%.2f')
    f.yaxis.axis_label = y1[0].name

    f.y_range = Range1d(start=0 if y_min == 0 else y_min - 0.1 * dy, end=y_max + 0.1 * dy)
    for y in y1:
        f.line(x=y.index, y=y, color='black')

    if y2:
        if is_x_time:
            zero = min(y.index.min() for y in y2)
            for y in y2:
                y.index = (y.index - zero).total_seconds()
        for y in y2:
            f.line(x=y.index, y=y, color='grey')

        y1, y2 = pd.concat(y1), pd.concat(y2)
        y2 = interpolate_to_index(y1, y2)
        y1, y2, range = delta_patches(y1, y2)
        f.extra_y_ranges = {'delta': range}
        if y1 is not None:
            f.patch(x=y1.index, y=y1, color='green', alpha=0.1, y_range_name='delta')
        if y2 is not None:
            f.patch(x=y2.index, y=y2, color='red', alpha=0.1, y_range_name='delta')

    # f.toolbar_location = None
    if x_range is not None:
        f.x_range = x_range

    return f


def cumulative(nx, ny, y1, y2=None, sample=10):

    y1 = pd.concat(y1)
    y1 = y1.sort_values(ascending=False).reset_index(drop=True)
    y_max = y1.max()
    y_min = y1.min()
    if y2 is not None:
        y2 = pd.concat(y2)
        y2 = y2.sort_values(ascending=False).reset_index(drop=True)
        y_max = max(y_max, y2.max())
        y_min = min(y_min, y2.min())
    dy = y_max - y_min

    f = figure(plot_width=nx, plot_height=ny,
               x_range=Range1d(start=y1.index.max() * sample, end=0),
               x_axis_type='datetime',
               x_axis_label=TIME,
               y_range=Range1d(start=0 if y_min == 0 else y_min - 0.1 * dy, end=y_max + 0.1 * dy),
               y_axis_location='right',
               y_axis_label=y1.name)
    f.xaxis[0].formatter = NumeralTickFormatter(format='00:00:00')

    f.line(x=y1.index * sample, y=y1, color='black')
    if y2 is not None:
        f.line(x=y2.index * sample, y=y2, color='grey')
        y1, y2, range = delta_patches(y1, y2)
        f.extra_y_ranges = {'delta': range}
        f.patch(x=y1.index * sample, y=y1, color='green', alpha=0.1, y_range_name='delta')
        f.patch(x=y2.index * sample, y=y2, color='red', alpha=0.1, y_range_name='delta')

    f.toolbar_location = None
    return f


def health(nx, ny, ftn, ftg, hr):

    f = figure(plot_width=nx, plot_height=ny, x_axis_type='datetime', tools=tools())
    f.toolbar.logo = None
    f.xaxis.axis_label = 'Date'

    max_f = ftn.max() * 1.1
    min_f = ftn.min() * 0.9

    f.y_range = Range1d(start=min_f, end=max_f)
    f.yaxis.axis_label = '%s, %s' % (ftn.name, ftg.name)
    f.yaxis[0].formatter = PrintfTickFormatter(format='')

    patch = closed_patch(ftg, zero=min_f)
    f.patch(x=patch.index, y=patch, color='grey', alpha=0.2)
    f.line(x=ftn.index, y=ftn, color='black')

    hr = hr.dropna()
    if len(hr):
        max_hr = hr.max() * 1.1
        min_hr = hr.min() * 0.9
        f.extra_y_ranges = {hr.name: Range1d(start=min_hr, end=max_hr)}
        f.add_layout(LinearAxis(y_range_name=hr.name, axis_label=hr.name), 'right')
        f.circle(x=hr.index, y=hr, color='red', alpha=0.2, y_range_name=hr.name)

    # f.toolbar_location = None
    return f


def activities(nx, ny, st, at):

    f = figure(plot_width=nx, plot_height=ny, x_axis_type='datetime', tools=tools())
    f.toolbar.logo = None
    f.xaxis.axis_label = 'Date'

    if st is not None and len(st):
        st = st.dropna()
        f.y_range = Range1d(start=0, end=1.1 * st.max())
        f.yaxis.axis_label = st.name
        f.vbar(x=st.index, width=dt.timedelta(hours=20), top=st, fill_color='grey', fill_alpha=0.4, line_alpha=0)
    else:
        f.yaxis[0].visible = False

    if at is not None and len(at):
        at = at.dropna()
        f.extra_y_ranges = {at.name: Range1d(start=0, end=at.max() * 1.1)}
        f.add_layout(LinearAxis(y_range_name=at.name, axis_label=at.name), 'right')
        f.circle(x=at.index, y=at, color='black', fill_alpha=0, y_range_name=at.name)
        f.yaxis[1].formatter = PrintfTickFormatter(format='')

    # f.toolbar_location = None
    return f


def heart_rate_zones(nx, ny, hrz):

    max_z, n_sub = 5, 5

    bins = pd.interval_range(start=1, end=max_z+1, periods=n_sub * max_z, closed='left')
    c = [palettes.Inferno[6][int(b.left)-1] for b in bins]
    hrz_categorized = pd.cut(hrz, bins)
    counts = hrz_categorized.groupby(hrz_categorized).count()

    f = figure(plot_width=nx, plot_height=ny, x_range=Range1d(start=1, end=max_z+1), x_axis_label=HR_ZONE)
    f.quad(left=counts.index.categories.left, right=counts.index.categories.right, top=counts, bottom=0,
           color=c, fill_alpha=0.2)
    f.yaxis.visible = False

    f.toolbar_location = None
    return f

