
import datetime as dt

import pandas as pd
from bokeh import palettes, tile_providers
from bokeh.models import NumeralTickFormatter, PrintfTickFormatter, Range1d, LinearAxis, PanTool, ZoomInTool, \
    HoverTool, ZoomOutTool, ResetTool, Spacer
from bokeh.plotting import figure

from .data_frame import interpolate_to_index, delta_patches, closed_patch
from ..stoats.names import TIME, HR_ZONE, CLIMB_DISTANCE, CLIMB_ELEVATION, ALTITUDE, LOCAL_TIME, SPHERICAL_MERCATOR_X, \
    SPHERICAL_MERCATOR_Y, FATIGUE, FITNESS, REST_HR, LONGITUDE, LATITUDE, CADENCE


def disable_toolbar(f):
    f.toolbar_location = None


def disable_logo(f):
    f.toolbar.logo = None


def range_all(source, axis, prev_min=None, prev_max=None):
    if source:
        mn, mx = prev_min, prev_max
        for df in source:
            if axis in df:
                clean = df[axis].dropna()
                if len(clean):
                    if mn is None:
                        mn, mx = clean.min(), clean.max()
                    else:
                        mn, mx = min(mn, clean.min()), max(mx, clean.max())
        return mn, mx
    else:
        return prev_min, prev_max


def make_hover(*names):
    labels = [(name, '@{%s}' % name) for name in names if name != TIME]
    labels += [(TIME, '@{%s}' % LOCAL_TIME)]
    return HoverTool(tooltips=labels)


def make_tools(x=None, y=None):
    tools = [PanTool(dimensions='width'),
             ZoomInTool(dimensions='width'), ZoomOutTool(dimensions='width'),
             ResetTool()]
    if x and y:
        tools.append(make_hover(x, y))
    return tools


def simple_map(n, xy1, xy2=None):
    f = figure(plot_width=n, plot_height=n, x_axis_type='mercator', y_axis_type='mercator')
    disable_toolbar(f)
    if xy2 is not None:
        f.line(x=SPHERICAL_MERCATOR_X, y=SPHERICAL_MERCATOR_Y, source=xy2,
               line_width=4, line_color='black', line_alpha=0.1)
    f.line(x=SPHERICAL_MERCATOR_X, y=SPHERICAL_MERCATOR_Y, source=xy1, line_color='black')
    f.axis.visible = False
    return f


def dot_map(n, xy1, xy2=None, with_tools=True):
    from ch2.bucket.page.activity_details import DISTANCE_KM

    if with_tools:
        hover = make_hover(DISTANCE_KM, LATITUDE, LONGITUDE)
        hover.renderers = []
        tools = [PanTool(), ZoomInTool(), ZoomOutTool(), ResetTool(), hover]
    else:
        tools = ''
    f = figure(plot_width=n, plot_height=n, x_axis_type='mercator', y_axis_type='mercator', tools=tools)
    disable_logo(f)

    for df in xy1:
        f.circle(x=SPHERICAL_MERCATOR_X, y=SPHERICAL_MERCATOR_Y, line_alpha=0, fill_color='red',
                 size='size', fill_alpha=0.03, source=df)
        renderer = f.line(x=SPHERICAL_MERCATOR_X, y=SPHERICAL_MERCATOR_Y, source=df, line_color='black')
        if with_tools:
            hover.renderers.append(renderer)

    if xy2 is not None:
        for df in xy2:
            renderer = f.line(x=SPHERICAL_MERCATOR_X, y=SPHERICAL_MERCATOR_Y, source=df, line_color='grey')
            if with_tools:
                hover.renderers.append(renderer)

    f.add_tile(tile_providers.STAMEN_TERRAIN, alpha=0.1)
    f.axis.visible = False

    return f


def line_diff_elevation_climbs(nx, ny, x_axis, y_axis, source1, source2=None, climbs=None, st=None, x_range=None):

    from .page.activity_details import DISTANCE_KM, ELEVATION_M

    f = line_diff(nx, ny, x_axis, y_axis, source1, source2=source2, x_range=x_range)

    for df in source1:
        if ALTITUDE in df and len(df[ALTITUDE].dropna()):
            f.line(x=x_axis, y=ALTITUDE, source=df, color='black', alpha=0.1, line_width=2)

    if climbs is not None:
        joined = pd.concat(st)
        for time, climb in climbs.iterrows():
            i = joined.index.get_loc(time, method='nearest')
            x = joined[DISTANCE_KM].iloc[i]
            x = (x - climb[CLIMB_DISTANCE] / 1000, x)
            y = joined[ELEVATION_M].iloc[i]
            y = (y - climb[CLIMB_ELEVATION], y)
            f.line(x=x, y=y, color='red', line_width=5, alpha=0.2)
            for xx, yy in zip(x, y):
                f.circle(x=xx, y=yy, color='red', size=8, alpha=0.2)

    return f


def line_diff_speed_cadence(nx, ny, x_axis, y_axis, source1, source2=None, x_range=None):
    f = line_diff(nx, ny, x_axis, y_axis, source1, source2=source2, x_range=x_range)
    if source2 is None:
        min_cd, max_cd = range_all(source1, CADENCE)
        if min_cd is not None and max_cd is not None:
            f.extra_y_ranges = {CADENCE: Range1d(start=min_cd * 0.9, end=max_cd * 1.1)}
            f.add_layout(LinearAxis(y_range_name=CADENCE, axis_label=CADENCE), 'right')
            for df in source1:
                if CADENCE in df and len(df[CADENCE].dropna()):
                    f.line(x=x_axis, y=CADENCE, source=df, line_dash='dotted', color='grey', y_range_name=CADENCE)
    return f


def make_series(source, y_axis, x_axis):
    all = []
    for df in source:
        s = df[y_axis]
        s.index = df[x_axis]
        all.append(s)
    return pd.concat(all)


def line_diff(nx, ny, x_axis, y_axis, source1, source2=None, x_range=None):

    is_x_time = x_axis == TIME

    if source1:
        tools = make_tools(y_axis, x_axis)
        hover = tools[-1]
        hover.renderers = []
    else:
        tools = ''
    f = figure(plot_width=nx, plot_height=ny, x_axis_type='datetime' if is_x_time else 'linear', tools=tools)
    disable_logo(f)

    y_min, y_max = range_all(source1, y_axis)
    if y_min is None:
        return f  # bail if no data
    y_min, y_max = range_all(source2, y_axis, y_min, y_max)
    dy = y_max - y_min

    if is_x_time:
        f.xaxis[0].formatter = NumeralTickFormatter(format='00:00:00')
        zero, _ = range_all(source1, y_axis)
        for df in source1:
            df[x_axis] = (df[x_axis] - zero).total_seconds()
    else:
        f.xaxis[0].formatter = PrintfTickFormatter(format='%.2f')
    f.xaxis.axis_label = x_axis
    f.yaxis.axis_label = y_axis

    f.y_range = Range1d(start=0 if y_min == 0 else y_min - 0.1 * dy, end=y_max + 0.1 * dy)
    for df in source1:
        hover.renderers.append(f.line(x=x_axis, y=y_axis, source=df, color='black'))

    if source2:
        if is_x_time:
            zero, _ = range_all(source2, x_axis)
            for df in source2:
                df[x_axis] = (df[x_axis] - zero).total_seconds()
        for df in source2:
            hover.renderers.append(f.line(x=x_axis, y=y_axis, source=df, color='grey'))

        y1, y2 = make_series(source1, y_axis, x_axis), make_series(source2, y_axis, x_axis)
        y2 = interpolate_to_index(y1, y2)
        y1, y2, range = delta_patches(y1, y2)
        f.extra_y_ranges = {'delta': range}
        if y1 is not None:
            f.patch(x=y1.index, y=y1, color='green', alpha=0.1, y_range_name='delta')
        if y2 is not None:
            f.patch(x=y2.index, y=y2, color='red', alpha=0.1, y_range_name='delta')

    if x_range is not None:
        f.x_range = x_range

    return f


def cumulative(nx, ny, y1, y2=None, sample=10):

    if not len(y1):
        return figure(plot_width=nx, plot_height=ny, tools="")

    y1 = y1.sort_values(ascending=False).reset_index(drop=True)
    y_max = y1.max()
    y_min = y1.min()
    if pd.isna(y_min):
        return Spacer()

    if y2 is not None and len(y2):
        y2 = y2.sort_values(ascending=False).reset_index(drop=True)
        y_max = max(y_max, y2.max())
        y_min = min(y_min, y2.min())
    dy = y_max - y_min

    f = figure(plot_width=nx, plot_height=ny,
               x_range=Range1d(start=y1.index.max() * sample, end=0),
               y_range=Range1d(start=0 if y_min == 0 else y_min - 0.1 * dy, end=y_max + 0.1 * dy),
               y_axis_location='right',
               y_axis_label=y1.name)
    disable_toolbar(f)
    f.xaxis.visible = False

    f.line(x=y1.index * sample, y=y1, color='black')
    if y2 is not None and len(y2):
        f.line(x=y2.index * sample, y=y2, color='grey')
        y1, y2, range = delta_patches(y1, y2)
        if len(y1) and len(y2):
            f.extra_y_ranges = {'delta': range}
            f.patch(x=y1.index * sample, y=y1, color='green', alpha=0.1, y_range_name='delta')
            f.patch(x=y2.index * sample, y=y2, color='red', alpha=0.1, y_range_name='delta')

    return f


def health(nx, ny, ff, hr, x_range=None):
    from .page.activity_details import LOG_FITNESS, LOG_FATIGUE

    hover = make_hover(FITNESS, FATIGUE)
    hover.renderers = []
    tools = make_tools()
    tools.append(hover)

    f = figure(plot_width=nx, plot_height=ny, x_axis_type='datetime', tools=tools)
    disable_logo(f)
    f.xaxis.axis_label = 'Date'

    max_f = ff[LOG_FITNESS].max() * 1.1
    min_f = ff[LOG_FITNESS].min() * 0.9
    f.y_range = Range1d(start=min_f, end=max_f)
    f.yaxis.axis_label = '%s, %s' % (LOG_FITNESS, LOG_FATIGUE)
    f.yaxis[0].formatter = PrintfTickFormatter(format='')

    patch = closed_patch(ff[LOG_FATIGUE], zero=min_f)
    f.patch(x=patch.index, y=patch, color='grey', alpha=0.2)
    hover.renderers.append(f.line(x=TIME, y=LOG_FITNESS, source=ff, color='black'))

    hr = hr[REST_HR].dropna()
    if len(hr):
        max_hr = hr.max() * 1.1
        min_hr = hr.min() * 0.9
        f.extra_y_ranges = {hr.name: Range1d(start=min_hr, end=max_hr)}
        f.add_layout(LinearAxis(y_range_name=hr.name, axis_label=hr.name), 'right')
        f.circle(x=hr.index, y=hr, color='red', alpha=0.2, y_range_name=hr.name)

    if x_range is not None:
        f.x_range = x_range

    return f


def activities(nx, ny, steps, active_time, x_range=None):

    f = figure(plot_width=nx, plot_height=ny, x_axis_type='datetime', tools=make_tools())
    disable_logo(f)
    f.xaxis.axis_label = 'Date'

    steps = None if steps is None else steps.dropna()
    active_time = None if active_time is None else active_time.dropna()

    if steps is not None and len(steps):
        f.y_range = Range1d(start=0, end=1.1 * steps.max())
        f.yaxis.axis_label = steps.name
        f.vbar(x=steps.index, width=dt.timedelta(hours=20), top=steps, fill_color='grey', fill_alpha=0.4, line_alpha=0)
    else:
        f.yaxis[0].visible = False

    if active_time is not None and len(active_time):
        f.extra_y_ranges = {active_time.name: Range1d(start=0, end=active_time.max() * 1.1)}
        f.add_layout(LinearAxis(y_range_name=active_time.name, axis_label=active_time.name), 'right')
        f.circle(x=active_time.index, y=active_time, color='black', fill_alpha=0, y_range_name=active_time.name)
        f.yaxis[1].formatter = PrintfTickFormatter(format='')

    if x_range is not None:
        f.x_range = x_range

    return f


def heart_rate_zones(nx, ny, hrz):

    max_z, n_sub = 5, 5

    bins = pd.interval_range(start=1, end=max_z+1, periods=n_sub * max_z, closed='left')
    c = [palettes.Inferno[6][int(b.left)-1] for b in bins]
    hrz_categorized = pd.cut(hrz, bins)
    counts = hrz_categorized.groupby(hrz_categorized).count()

    f = figure(plot_width=nx, plot_height=ny, x_range=Range1d(start=1, end=max_z+1), x_axis_label=HR_ZONE)
    disable_toolbar(f)
    f.quad(left=counts.index.categories.left, right=counts.index.categories.right, top=counts, bottom=0,
           color=c, fill_alpha=0.2)
    f.yaxis.visible = False

    return f
