
import datetime as dt
from logging import getLogger

import numpy as np
import pandas as pd
from bokeh import palettes, tile_providers
from bokeh.layouts import column, row
from bokeh.models import PanTool, ZoomInTool, ZoomOutTool, ResetTool, HoverTool, Range1d, LinearAxis, Title, Band, \
    ColumnDataSource
from bokeh.plotting import figure
from math import sqrt
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import PolynomialFeatures

from .utils import tooltip, make_range
from ..frame import present
from ...names import N

log = getLogger(__name__)

STAMEN_TERRAIN = tile_providers.get_provider(tile_providers.Vendors.STAMEN_TERRAIN)
DEFAULT_BACKEND = 'webgl'
MAP_BACKEND = 'canvas'  # weird results with webgl

# todo - make selection of hover tool with name='with_hover' universal


def subtract(a, c, key, col):
    cols = [key, col]
    limit = min(a[key].max(), c[key].max())
    a = a.loc[a[key] <= limit, cols]
    c = c.loc[c[key] <= limit, cols]
    both = a.merge(c, how='outer', on=key, sort=True, suffixes=('_a', '_c'))
    both.interpolate(inplace=True, limit_direction='both')
    return pd.DataFrame({col: both[col + '_a'] - both[col + '_c'], key: both[key]})


def patches(x, y, diff):
    y = diff.set_index(x)[y]
    range = y.abs().max() * 1.1
    green = y.clip(lower=0).append(pd.Series([0, 0], index=[y.index[len(y) - 1], y.index[0]]))
    red = y.clip(upper=0).append(pd.Series([0, 0], index=[y.index[len(y) - 1], y.index[0]]))
    return green, red, Range1d(start=-range, end=range)


def add_tsid_line(f, x, y, source, color='black', line_dash='solid'):
    for _, s in source.groupby(N.TIMESPAN_ID):
        f.line(x=x, y=y, source=s, line_color=color, line_dash=line_dash, name='with_hover')


def comparison_line_plot(nx, ny, x, y, source, other=None, ylo=None, yhi=None, x_range=None,
                         output_backend=DEFAULT_BACKEND):
    if not present(source, x, y): return None
    tools = [PanTool(dimensions='width'),
             ZoomInTool(dimensions='width'), ZoomOutTool(dimensions='width'),
             ResetTool(),
             HoverTool(tooltips=[tooltip(x)
                                 for x in (y, N.DISTANCE_KM, N.LOCAL_TIME)], names=['with_hover'])]
    f = figure(output_backend=output_backend, plot_width=nx, plot_height=ny,
               x_axis_type='datetime' if N.TIME in x else 'linear', tools=tools)
    f.y_range = make_range(source[y], lo=ylo, hi=yhi)  # was this ignored previously?
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


def add_hr_zones(f, df, x, hr_zones):
    left, right = df[x].min(), df[x].max()
    # we want to start by highlighting zone 2 so we drop 1 completely
    for bottom, top in list(zip(hr_zones[1:], hr_zones[2:] + [999]))[::2]:
        f.quad(top=top, bottom=bottom, left=left, right=right, color='black', alpha=0.05)
    return f


def add_cum_line(f, y, source, color='black', line_dash='solid'):
    y_c = source[y].sort_values(ascending=False).reset_index(drop=True)
    f.line(x=y_c.index, y=y_c, line_color=color, line_dash=line_dash)
    f.x_range = Range1d(start=y_c.index.max(), end=y_c.index.min())
    df = y_c.to_frame('y')
    df['x'] = df.index
    return df


def cumulative_plot(nx, ny, y, source, other=None, ylo=None, yhi=None, output_backend=DEFAULT_BACKEND):
    if not present(source, y): return None
    f = figure(output_backend=output_backend, plot_width=nx, plot_height=ny, y_axis_location='right')
    f.y_range = make_range(source[y], lo=ylo, hi=yhi)
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
    if f is not None and present(climbs, N.CLIMB_DISTANCE):
        for time, climb in climbs.loc[~pd.isna(climbs[N.CLIMB_DISTANCE])].iterrows():
            i = source.index.get_loc(time, method='nearest')
            x = source[N.DISTANCE_KM].iloc[i]
            x = (x, x + climb[N.CLIMB_DISTANCE])
            y = source[N.ELEVATION_M].iloc[i]
            y = (y, y + climb[N.CLIMB_ELEVATION])
            f.line(x=x, y=y, color='red', line_width=5, alpha=0.2)
            for xx, yy in zip(x, y):
                f.circle(x=xx, y=yy, color='red', size=8, alpha=0.2)


def add_climb_zones(f, climbs, source):
    if f is not None and present(climbs, N.CLIMB_DISTANCE):
        for time, climb in climbs.loc[~pd.isna(climbs[N.CLIMB_DISTANCE])].iterrows():
            i = source.index.get_loc(time, method='nearest')
            left = source[N.DISTANCE_KM].iloc[i]
            right = left + climb[N.CLIMB_DISTANCE]
            top = f.y_range.end
            bottom = f.y_range.start
            f.quad(top=top, bottom=bottom, left=left, right=right, color='red', alpha=0.05)


def histogram_plot(nx, ny, x, source, xlo=None, xhi=None, nsub=5, output_backend=DEFAULT_BACKEND):
    if not present(source, x): return None
    xlo, xhi = source[x].min() if xlo is None else xlo, source[x].max() if xhi is None else xhi
    bins = pd.interval_range(start=xlo, end=xhi, periods=nsub * (xhi - xlo), closed='left')
    c = [palettes.Inferno[int(xhi - xlo + 1)][int(b.left - xlo)] for b in bins]
    hrz_categorized = pd.cut(source[x], bins)
    counts = hrz_categorized.groupby(hrz_categorized).count()
    f = figure(output_backend=output_backend, plot_width=nx, plot_height=ny, x_range=Range1d(start=xlo, end=xhi),
               x_axis_label=x)
    f.quad(left=counts.index.categories.left, right=counts.index.categories.right, top=counts, bottom=0,
           color=c, fill_alpha=0.2)
    f.toolbar_location = None
    f.yaxis.visible = False
    return f


def add_route(f, source, color='black', line_dash='solid'):
    return f.line(x=N.SPHERICAL_MERCATOR_X, y=N.SPHERICAL_MERCATOR_Y, source=source,
                  color=color, line_dash=line_dash)


def add_start_finish(f, source, start='green', finish='red'):
    source = source.iloc[[0, -1]]
    source = source.reset_index(drop=True)
    source.loc[0, N.COLOR] = start
    source.loc[1, N.COLOR] = finish
    return f.circle(x=N.SPHERICAL_MERCATOR_X, y=N.SPHERICAL_MERCATOR_Y, source=source, color=N.COLOR)


def map_plot(nx, ny, source, other=None, output_backend=MAP_BACKEND):
    tools = [PanTool(dimensions='both'),
             ZoomInTool(dimensions='both'), ZoomOutTool(dimensions='both'),
             ResetTool(),
             HoverTool(tooltips=[tooltip(x)
                                 for x in (N.LATITUDE, N.LONGITUDE, N.DISTANCE_KM, N.LOCAL_TIME)])]
    f = figure(output_backend=output_backend, plot_width=nx, plot_height=ny,
               x_axis_type='mercator', y_axis_type='mercator', match_aspect=True, tools=tools)
    add_route(f, source)
    if present(other, N.SPHERICAL_MERCATOR_X, N.SPHERICAL_MERCATOR_Y):
        add_route(f, other, color='black', line_dash='dotted')
    f.add_tile(STAMEN_TERRAIN, alpha=0.3)
    f.axis.visible = False
    f.toolbar.logo = None
    return f


def map_intensity(nx, ny, source, z, power=1.0, color='red', alpha=0.01, ranges=None, output_backend=MAP_BACKEND):
    if not present(source, z): return None
    tools = [PanTool(dimensions='both'),
             ZoomInTool(dimensions='both'), ZoomOutTool(dimensions='both'),
             ResetTool(),
             HoverTool(tooltips=[tooltip(x) for x in (z, N.DISTANCE_KM, N.LOCAL_TIME)])]
    f = figure(output_backend=output_backend, plot_width=nx, plot_height=ny,
               x_axis_type='mercator', y_axis_type='mercator', title=z, match_aspect=True, tools=tools)
    tools[-1].renderers = [add_route(f, source)]
    mn, mx = source[z].min(), source[z].max()
    source['size'] = sqrt(nx * ny) * ((source[z] - mn) / (mx - mn)) ** power / 10
    f.circle(x=N.SPHERICAL_MERCATOR_X, y=N.SPHERICAL_MERCATOR_Y, size='size', source=source, color=color, alpha=alpha)
    f.axis.visible = False
    f.toolbar.logo = None
    if ranges is not None:
        f.x_range = ranges.x_range
        f.y_range = ranges.y_range
    return f


def map_intensity_signed(nx, ny, source, z, power=1.0, color='red', color_neg='blue', alpha=0.01, ranges=None,
                         output_backend=MAP_BACKEND):
    if not present(source, z): return None
    tools = [PanTool(dimensions='both'),
             ZoomInTool(dimensions='both'), ZoomOutTool(dimensions='both'),
             ResetTool(),
             HoverTool(tooltips=[tooltip(x) for x in (z, N.DISTANCE_KM, N.LOCAL_TIME)])]
    f = figure(output_backend=output_backend, plot_width=nx, plot_height=ny,
               x_axis_type='mercator', y_axis_type='mercator', title=z, match_aspect=True, tools=tools)
    tools[-1].renderers = [add_route(f, source)]
    mn, mx = source[z].min(), source[z].max()
    scale = max(mx, -mn)
    if mx > 0:
        source['size'] = np.sign(source[z]) * sqrt(nx * ny) * (np.abs(source[z]) / scale) ** power / 10
        source['size'].clip(lower=0, inplace=True)
        f.circle(x=N.SPHERICAL_MERCATOR_X, y=N.SPHERICAL_MERCATOR_Y, size='size', source=source,
                 color=color, alpha=alpha)
    if mn < 0:
        source['size'] = -np.sign(source[z]) * sqrt(nx * ny) * (np.abs(source[z]) / scale) ** power / 10
        source['size'].clip(lower=0, inplace=True)
        f.circle(x=N.SPHERICAL_MERCATOR_X, y=N.SPHERICAL_MERCATOR_Y, size='size', source=source,
                 color=color_neg, alpha=alpha)
    f.axis.visible = False
    f.toolbar.logo = None
    if ranges is not None:
        f.x_range = ranges.x_range
        f.y_range = ranges.y_range
    return f


def map_thumbnail(nx, ny, source, sample='1min', caption=True, title=True, output_backend=MAP_BACKEND):
    f = figure(output_backend=output_backend, plot_width=nx, plot_height=ny,
               x_axis_type='mercator', y_axis_type='mercator', match_aspect=True,
               title=(source.index[0].strftime('%Y-%m-%d') if title else None))
    xy = source.loc[source[N.SPHERICAL_MERCATOR_X].notna() & source[N.SPHERICAL_MERCATOR_Y].notna(),
                    [N.SPHERICAL_MERCATOR_X, N.SPHERICAL_MERCATOR_Y]].resample(sample).mean()
    add_route(f, xy)
    add_start_finish(f, xy)
    f.axis.visible = False
    f.toolbar_location = None
    return f


def first_value(df, name):
    col = df[name]
    return col.loc[col.first_valid_index()]


def add_map_caption(f, df):
    caption = ''
    if present(df, N.ACTIVE_DISTANCE):
        caption += '%dkm' % int(0.5 + first_value(df, N.ACTIVE_DISTANCE) / 1000)
    if present(df, N.ACTIVE_TIME):
        if caption: caption += '/'
        caption += '%.1fhr' % (first_value(df, N.ACTIVE_TIME) / 3600)
    if present(df, N.TOTAL_CLIMB):
        if caption: caption += '/'
        caption += '%dm' % int(first_value(df, N.TOTAL_CLIMB))
    if caption:
        f.add_layout(Title(text=caption, align="left"), "below")


def line_plotter():
    return lambda f, *args, **kargs: f.line(*args, **kargs)


def comb_plotter():
    def plotter(f, x=None, y=None, source=None, **kargs):
        xs = [(value, value) for value in source[x]]
        ys = [(0, value) for value in source[y]]
        f.multi_line(xs, ys, **kargs)

    return plotter


def dot_plotter():
    return lambda f, *args, **kargs: f.circle(*args, **kargs)


def bar_plotter(delta):
    def plotter(f, x=None, y=None, source=None, **kargs):
        f.vbar(x=x, width=delta, top=y, source=source, **kargs)

    return plotter


def multi_line_plot(nx, ny, x, ys, source, colors, alphas=None, x_range=None, y_label=None, rescale=False,
                    output_backend=DEFAULT_BACKEND):
    return multi_plot(nx, ny, x, ys, source, colors, alphas=alphas, x_range=x_range, y_label=y_label, rescale=rescale,
                      plotters=[line_plotter()], output_backend=output_backend)


def multi_dot_plot(nx, ny, x, ys, source, colors, alphas=None, x_range=None, y_label=None, rescale=False,
                    output_backend=DEFAULT_BACKEND):
    return multi_plot(nx, ny, x, ys, source, colors, alphas=alphas, x_range=x_range, y_label=y_label, rescale=rescale,
                      plotters=[dot_plotter()], output_backend=output_backend)


def multi_bar_plot(nx, ny, x, ys, source, colors, alphas=None, x_range=None, y_label=None, rescale=False,
                    output_backend=DEFAULT_BACKEND):
    return multi_plot(nx, ny, x, ys, source, colors, alphas=alphas, x_range=x_range, y_label=y_label, rescale=rescale,
                      plotters=[bar_plotter(dt.timedelta(hours=20))], output_backend=output_backend)


def multi_plot(nx, ny, x, ys, source, colors, alphas=None, x_range=None, y_label=None, rescale=False,
               plotters=None, output_backend=DEFAULT_BACKEND):
    if not ys or not present(source, x, *ys): return None
    tools = [PanTool(dimensions='width'),
             ZoomInTool(dimensions='width'), ZoomOutTool(dimensions='width'),
             ResetTool(),
             HoverTool(tooltips=[tooltip(x) for x in ys + [N.LOCAL_TIME]], names=['with_hover'])]
    f = figure(output_backend=output_backend, plot_width=nx, plot_height=ny,
               x_axis_type='datetime' if N.TIME in x else 'linear', tools=tools)
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
        y_range = make_range(source[y])
        if rescale and y != ys[0]:
            f.extra_y_ranges[y] = y_range
            f.add_layout(LinearAxis(y_range_name=y, axis_label=y), 'right')
            plotter(f, x=x, y=y, source=source, color=color, alpha=alpha, y_range_name=y, name='with_hover')
        else:
            f.y_range = y_range
            plotter(f, x=x, y=y, source=source, color=color, alpha=alpha, name='with_hover')
    f.xaxis.axis_label = x
    f.toolbar.logo = None
    if ny < 300: f.toolbar_location = None
    if x_range: f.x_range = x_range
    return f


def add_multi_line_at_index(f, x, ys, source, colors, alphas=None, dash='dotted', index=-1):
    if f:
        if alphas is None: alphas = [0.5 for y in ys]
        for y, color, alpha in zip(ys, colors, alphas):
            f.line(x=x, y=source[y].loc[source[y].notna()].iloc[index],
                   source=source, color=color, alpha=alpha, line_dash=dash)


def add_band(f, x, ylo, yhi, source, color, alpha=0.3, y_range_name='default'):
    if f:
        band = Band(base=x, lower=ylo, upper=yhi, source=ColumnDataSource(source),
                    fill_color=color, fill_alpha=alpha, line_width=1, line_color=color,
                    y_range_name=y_range_name)
        f.add_layout(band)


def add_curve(f, x, y, source, group_size=30, color='black', alpha=1, smooth=1, y_range_name='default'):
    if f:
        # https://scikit-learn.org/stable/auto_examples/linear_model/plot_polynomial_interpolation.html
        source = source[[x, y]].dropna()
        degree = min(10, max(1, len(source) // group_size))
        log.debug(f'Fitting polynomial of degree {degree} (ridge alpha {smooth})')
        xf = source[x].values.astype('float64')
        nxf = (xf - xf[0]) / (xf[1] - xf[0])
        nxf2 = nxf[:, np.newaxis]
        y2 = source[y].values[:, np.newaxis]
        model = make_pipeline(PolynomialFeatures(degree), Ridge(alpha=smooth))
        model.fit(nxf2, y2)
        f.line(source[x], model.predict(nxf2)[:, 0], color=color, alpha=alpha, y_range_name=y_range_name)


def htile(maps, n):
    return column([row(maps[i:i + n]) for i in range(0, len(maps), n)])


def vtile(maps, n):
    return row([column(maps[i::n]) for i in range(n)])
