
from bokeh.models import PanTool, ZoomInTool, ZoomOutTool, ResetTool, HoverTool, LinearAxis
from bokeh.plotting import figure

from .line import multi_dot_plot, dot_plotter, comb_plotter, DEFAULT_BACKEND
from .utils import make_range, evenly_spaced_hues, tooltip
from ..frame import related_statistics
from ...stats.names import ACTIVE_TIME, ACTIVE_DISTANCE, TIME, ACTIVE_TIME_H, ACTIVE_DISTANCE_KM, LOCAL_TIME, _slash, \
    H, KM, ACTIVITY_GROUP, like, _delta, FITNESS_D_ANY, FATIGUE_D_ANY


def std_distance_time_plot(nx, ny, source, x_range=None, output_backend=DEFAULT_BACKEND):
    # avoid range errors
    if len(source[ACTIVE_TIME].dropna()) < 2:
        return None
    groups = [group for statistic, group in related_statistics(source, ACTIVE_TIME)]
    if not groups:
        # original monochrome plot
        return multi_dot_plot(nx, ny, TIME, [ACTIVE_TIME_H, ACTIVE_DISTANCE_KM], source,
                              ['black', 'grey'], alphas=[1, 0.5], x_range=x_range, rescale=True)
    times = [f'{ACTIVE_TIME} ({group})' for group in groups]
    distances = [f'{ACTIVE_DISTANCE} ({group})' for group in groups]
    time_y_range = make_range(source[ACTIVE_TIME_H])
    distance_y_range = make_range(source[ACTIVE_DISTANCE_KM])
    colours = list(evenly_spaced_hues(len(groups)))
    tooltip_names = [ACTIVE_TIME_H, ACTIVE_DISTANCE_KM, ACTIVITY_GROUP, LOCAL_TIME]
    tooltip_names += [name for name in like(_delta(FITNESS_D_ANY), source.columns) if '(' not in name]
    tooltip_names += [name for name in like(_delta(FATIGUE_D_ANY), source.columns) if '(' not in name]
    tools = [PanTool(dimensions='width'),
             ZoomInTool(dimensions='width'), ZoomOutTool(dimensions='width'),
             ResetTool(),
             HoverTool(tooltips=[tooltip(name) for name in tooltip_names], names=['with_hover'])]
    f = figure(output_backend=output_backend, plot_width=nx, plot_height=ny, x_axis_type='datetime', tools=tools)
    f.yaxis.axis_label = f'lines - {ACTIVE_TIME_H}'
    f.y_range = time_y_range
    f.extra_y_ranges = {ACTIVE_DISTANCE: distance_y_range}
    f.add_layout(LinearAxis(y_range_name=ACTIVE_DISTANCE, axis_label=f'dots - {ACTIVE_DISTANCE_KM}'), 'right')
    plotter = comb_plotter()
    for time, colour in zip(times, colours):
        time_h = _slash(time, H)
        source[time_h] = source[time] / 3600
        plotter(f, x=TIME, y=time_h, source=source, color=colour, alpha=1)
    plotter = dot_plotter()
    for distance, colour in zip(distances, colours):
        distance_km = _slash(distance, KM)
        source[distance_km] = source[distance] / 1000
        plotter(f, x=TIME, y=distance_km, source=source, color=colour, alpha=1, name='with_hover',
                y_range_name=ACTIVE_DISTANCE)
    f.xaxis.axis_label = TIME
    f.toolbar.logo = None
    if ny < 300: f.toolbar_location = None
    if x_range: f.x_range = x_range
    return f
