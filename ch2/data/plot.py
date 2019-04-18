
import datetime as dt
from math import sqrt

import pandas as pd
from bokeh import palettes, tile_providers
from bokeh.layouts import column, row
from bokeh.models import PanTool, ZoomInTool, ZoomOutTool, ResetTool, HoverTool, Range1d, LinearAxis
from bokeh.plotting import figure

from .frame import present
from ..stoats.names import LOCAL_TIME, TIMESPAN_ID, TIME, CLIMB_DISTANCE, CLIMB_ELEVATION, SPHERICAL_MERCATOR_X, \
    SPHERICAL_MERCATOR_Y, LATITUDE, LONGITUDE, DISTANCE_KM, ELEVATION_M


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


def box_plot(f, col):
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


def tooltip(name):
    return name, '@{%s}' % name


def make_tools(y):
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


def y_range(f, y, source, ylo=None, yhi=None):
    ylo, yhi = source[y].dropna().min() if ylo is None else ylo, source[y].dropna().max() if yhi is None else yhi
    dy = yhi - ylo
    f.y_range = Range1d(start=ylo - 0.1 * dy, end=yhi + 0.1 * dy)


def add_tsid_line(f, x, y, source, color='black', line_dash='solid'):
    for _, s in source.groupby(TIMESPAN_ID):
        f.line(x=x, y=y, source=s, line_color=color, line_dash=line_dash)


def comparison_line_plot(nx, ny, x, y, source, other=None, ylo=None, yhi=None, x_range=None):
    f = figure(plot_width=nx, plot_height=ny, x_axis_type='datetime' if TIME in x else 'linear', tools=make_tools(y))
    y_range(f, y, source, ylo=ylo, yhi=yhi)
    add_tsid_line(f, x, y, source)
    if present(other, y):
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


def add_cum_line(f, y, source, color='black', line_dash='solid'):
    y_c = source[y].sort_values(ascending=False).reset_index(drop=True)
    f.line(x=y_c.index, y=y_c, line_color=color, line_dash=line_dash)
    f.x_range = Range1d(start=y_c.index.max(), end=y_c.index.min())
    df = y_c.to_frame('y')
    df['x'] = df.index
    return df


def cumulative_plot(nx, ny, y, source, other=None, ylo=None, yhi=None):
    f = figure(plot_width=nx, plot_height=ny, y_axis_location='right')
    y_range(f, y, source, ylo=ylo, yhi=yhi)
    y1 = add_cum_line(f, y, source)
    if present(other, y):
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
    for time, climb in climbs.loc[~pd.isna(climbs[CLIMB_DISTANCE])].iterrows():
        i = source.index.get_loc(time, method='nearest')
        x = source[DISTANCE_KM].iloc[i]
        x = (x - climb[CLIMB_DISTANCE] / 1000, x)
        y = source[ELEVATION_M].iloc[i]
        y = (y - climb[CLIMB_ELEVATION], y)
        f.line(x=x, y=y, color='red', line_width=5, alpha=0.2)
        for xx, yy in zip(x, y):
            f.circle(x=xx, y=yy, color='red', size=8, alpha=0.2)


def histogram_plot(nx, ny, x, source, xlo=None, xhi=None, nsub=5):
    xlo, xhi = source[x].min() if xlo is None else xlo, source[x].max() if xhi is None else xhi
    bins = pd.interval_range(start=xlo, end=xhi, periods=nsub * (xhi - xlo), closed='left')
    c = [palettes.Inferno[int(xhi-xlo+1)][int(b.left-xlo)] for b in bins]
    hrz_categorized = pd.cut(source[x], bins)
    counts = hrz_categorized.groupby(hrz_categorized).count()
    f = figure(plot_width=nx, plot_height=ny, x_range=Range1d(start=xlo, end=xhi), x_axis_label=x)
    f.quad(left=counts.index.categories.left, right=counts.index.categories.right, top=counts, bottom=0,
           color=c, fill_alpha=0.2)
    f.toolbar_location = None
    f.yaxis.visible = False
    return f


def add_route(f, source, color='black', line_dash='solid'):
    return f.line(x=SPHERICAL_MERCATOR_X, y=SPHERICAL_MERCATOR_Y, source=source,
                  color=color, line_dash=line_dash)


def map_plot(nx, ny, source, other=None):
    tools = [PanTool(dimensions='both'),
             ZoomInTool(dimensions='both'), ZoomOutTool(dimensions='both'),
             ResetTool(),
             HoverTool(tooltips=[tooltip(x) for x in (LATITUDE, LONGITUDE, DISTANCE_KM, LOCAL_TIME)])]
    f = figure(plot_width=nx, plot_height=ny, x_axis_type='mercator', y_axis_type='mercator', tools=tools)
    add_route(f, source)
    if present(other, SPHERICAL_MERCATOR_X, SPHERICAL_MERCATOR_Y):
        add_route(f, other, color='black', line_dash='dotted')
    f.add_tile(tile_providers.STAMEN_TERRAIN, alpha=0.3)
    f.axis.visible = False
    f.toolbar.logo = None
    return f


def map_intensity(nx, ny, source, z, power=1.0, color='red', alpha=0.01, ranges=None):
    tools = [PanTool(dimensions='both'),
             ZoomInTool(dimensions='both'), ZoomOutTool(dimensions='both'),
             ResetTool(),
             HoverTool(tooltips=[tooltip(x) for x in (z, DISTANCE_KM, LOCAL_TIME)])]
    f = figure(plot_width=nx, plot_height=ny, x_axis_type='mercator', y_axis_type='mercator',
               title=z, tools=tools)
    tools[-1].renderers = [add_route(f, source)]
    mn, mx = source[z].min(), source[z].max()
    source['size'] = sqrt(nx * ny) * ((source[z] - mn) / (mx - mn)) ** power / 10
    f.circle(x=SPHERICAL_MERCATOR_X, y=SPHERICAL_MERCATOR_Y, size='size', source=source, color=color, alpha=alpha)
    f.axis.visible = False
    f.toolbar.logo = None
    if ranges is not None:
        f.x_range = ranges.x_range
        f.y_range = ranges.y_range
    return f


def map_thumbnail(nx, ny, source, other=None):
    f = figure(plot_width=nx, plot_height=ny, x_axis_type='mercator', y_axis_type='mercator',
               title=source.index[0].strftime('%Y-%m-%d'))
    add_route(f, source)
    f.axis.visible = False
    f.toolbar_location = None
    return f


def line_plotter():
    return lambda f, *args, **kargs: f.line(*args, **kargs)


def dot_plotter():
    return lambda f, *args, **kargs: f.circle(*args, **kargs)


def bar_plotter(delta):
    def plotter(f, x=None, y=None, source=None, **kargs):
        f.vbar(x=x, width=delta, top=y, source=source, **kargs)
    return plotter


def multi_line_plot(nx, ny, x, ys, source, colors, alphas=None, x_range=None, y_label=None, rescale=False):
    return multi_plot(nx, ny, x, ys, source, colors, alphas=alphas, x_range=x_range, y_label=y_label, rescale=rescale,
                      plotters=[line_plotter()])


def multi_dot_plot(nx, ny, x, ys, source, colors, alphas=None, x_range=None, y_label=None, rescale=False):
    return multi_plot(nx, ny, x, ys, source, colors, alphas=alphas, x_range=x_range, y_label=y_label, rescale=rescale,
                      plotters=[dot_plotter()])


def multi_bar_plot(nx, ny, x, ys, source, colors, alphas=None, x_range=None, y_label=None, rescale=False):
    return multi_plot(nx, ny, x, ys, source, colors, alphas=alphas, x_range=x_range, y_label=y_label, rescale=rescale,
                      plotters=[bar_plotter(dt.timedelta(hours=20))])


def multi_plot(nx, ny, x, ys, source, colors, alphas=None, x_range=None, y_label=None, rescale=False,
               plotters=None):
    tools = [PanTool(dimensions='width'),
             ZoomInTool(dimensions='width'), ZoomOutTool(dimensions='width'),
             ResetTool(),
             HoverTool(tooltips=[tooltip(x) for x in ys + [LOCAL_TIME]])]
    f = figure(plot_width=nx, plot_height=ny, x_axis_type='datetime' if TIME in x else 'linear', tools=tools)
    if y_label:
        f.yaxis.axis_label = y_label
    elif rescale:
        f.yaxis.axis_label = ys[0]
    else:
        f.yaxis.axis_label = ', '.join(ys)
    if rescale: f.extra_y_ranges = {}
    if alphas is None: alphas = [1 for _ in ys]
    while len(plotters) < len(ys): plotters += plotters
    for y, color, alpha, plotter in zip(ys, colors, alphas, plotters):
        mn, mx = source[y].dropna().min(), source[y].dropna().max()
        dy = mx - mn
        if rescale and y != ys[0]:
            f.extra_y_ranges[y] = Range1d(start=mn - 0.1 * dy, end=mx + 0.1 * dy)
            f.add_layout(LinearAxis(y_range_name=y, axis_label=y), 'right')
            plotter(f, x=x, y=y, source=source, color=color, alpha=alpha, y_range_name=y)
        else:
            f.y_range = Range1d(start=mn - 0.1 * dy, end=mx + 0.1 * dy)
            plotter(f, x=x, y=y, source=source, color=color, alpha=alpha)
    f.xaxis.axis_label = x
    f.toolbar.logo = None
    if ny < 300: f.toolbar_location = None
    if x_range: f.x_range = x_range
    return f


def tile(maps, n):
    return column([row(maps[i:i+n]) for i in range(0, len(maps), n)])