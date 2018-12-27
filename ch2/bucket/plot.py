
import datetime as dt

import pandas as pd
from bokeh.models import NumeralTickFormatter, PrintfTickFormatter, Range1d, LinearAxis
from bokeh.palettes import Inferno
from bokeh.plotting import figure
from bokeh.tile_providers import STAMEN_TERRAIN

from .data_frame import interpolate_to_index, delta_patches, closed_patch
from ..stoats.names import TIME, HR_ZONE


def dot_map(n, x1, y1, size, x2=None, y2=None):

    f = figure(plot_width=n, plot_height=n, x_axis_type='mercator', y_axis_type='mercator')
    f.circle(x=x1, y=y1, line_alpha=0, fill_color='red', size=size, fill_alpha=0.03)
    f.line(x=x1, y=y1, line_color='black')

    if x2 is not None:
        f.line(x=x2, y=y2, line_color='grey')

    f.add_tile(STAMEN_TERRAIN, alpha=0.1)
    f.axis.visible = False

    f.toolbar_location = None
    return f


def line_diff(nx, ny, xlabel, y1, y2=None):

    is_time = isinstance(y1.index[0], dt.datetime)
    f = figure(plot_width=nx, plot_height=ny, x_axis_type='datetime' if is_time else 'linear')

    if is_time:
        f.xaxis.axis_label = 'Time'
        f.xaxis[0].formatter = NumeralTickFormatter(format='00:00:00')
        y1.index = (y1.index - y1.index[0]).total_seconds()
    else:
        f.xaxis.axis_label = xlabel
        f.xaxis[0].formatter = PrintfTickFormatter(format='%.3f')

    scale = y1.max()
    if y2 is not None:
        scale = max(scale, y2.max())

    f.line(x=y1.index, y=y1, color='black')
    f.y_range = Range1d(start=0, end=scale * 1.1)
    f.yaxis.axis_label = y1.name

    if y2 is not None:
        if is_time:
            y2.index = (y2.index - y2.index[0]).total_seconds()
        y2 = interpolate_to_index(y1, y2)
        f.line(x=y2.index, y=y2, color='grey')

        y1, y2, range = delta_patches(y1, y2)
        f.extra_y_ranges = {'delta': range}
        if y1 is not None:
            f.patch(x=y1.index, y=y1, color='green', alpha=0.1, y_range_name='delta')
        if y2 is not None:
            f.patch(x=y2.index, y=y2, color='red', alpha=0.1, y_range_name='delta')

    f.toolbar_location = None
    return f


def cumulative(nx, ny, y1, y2=None, sample=10):

    y1 = y1.sort_values(ascending=False).reset_index(drop=True)
    scale = y1.max()
    if y2 is not None:
        y2 = y2.sort_values(ascending=False).reset_index(drop=True)
        scale = max(scale, y2.max())

    f = figure(plot_width=nx, plot_height=ny,
               x_range=Range1d(start=y1.index.max() * sample, end=0),
               x_axis_type='datetime',
               x_axis_label=TIME,
               y_range=Range1d(start=0, end=scale * 1.1),
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

    f = figure(plot_width=nx, plot_height=ny, x_axis_type='datetime')
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
        f.extra_y_ranges = {hr.name: Range1d(start=25, end=70)}
        f.add_layout(LinearAxis(y_range_name=hr.name, axis_label=hr.name), 'right')
        f.circle(x=hr.index, y=hr, color='red', alpha=0.2, y_range_name=hr.name)

    f.toolbar_location = None
    return f


def activity(nx, ny, st, at):

    f = figure(plot_width=nx, plot_height=ny, x_axis_type='datetime')
    f.xaxis.axis_label = 'Date'

    st = st.dropna()
    if len(st):
        f.y_range = Range1d(start=0, end=1.1 * st.max())
        f.yaxis.axis_label = st.name
        f.vbar(x=st.index, width=dt.timedelta(hours=20), top=st, fill_color='grey', fill_alpha=0.4, line_alpha=0)
    else:
        f.yaxis[0].visible = False

    at = at.dropna()
    if len(at):
        f.extra_y_ranges = {at.name: Range1d(start=0, end=at.max() * 1.1)}
        f.add_layout(LinearAxis(y_range_name=at.name, axis_label=at.name), 'right')
        f.circle(x=at.index, y=at, color='black', fill_alpha=0, y_range_name=at.name)
        f.yaxis[1].formatter = PrintfTickFormatter(format='')

    f.toolbar_location = None
    return f


def heart_rate_zones(nx, ny, hrz):

    max_z, n_sub = 5, 5

    bins = pd.interval_range(start=1, end=max_z+1, periods=n_sub * max_z, closed='left')
    c = [Inferno[6][int(b.left)-1] for b in bins]
    hrz_categorized = pd.cut(hrz, bins)
    counts = hrz_categorized.groupby(hrz_categorized).count()

    f = figure(plot_width=nx, plot_height=ny, x_range=Range1d(start=1, end=max_z+1), x_axis_label=HR_ZONE)
    f.quad(left=counts.index.categories.left, right=counts.index.categories.right, top=counts, bottom=0,
           color=c, fill_alpha=0.2)
    f.yaxis.visible = False

    f.toolbar_location = None
    return f

