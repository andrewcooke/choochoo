
from bokeh.models import PanTool, ZoomInTool, ZoomOutTool, ResetTool, HoverTool, LinearAxis
from bokeh.plotting import figure

from .line import multi_dot_plot, dot_plotter, comb_plotter, DEFAULT_BACKEND
from .utils import make_range, evenly_spaced_hues, tooltip
from ..frame import related_statistics
from ...names import Names as N, like, Units


def std_distance_time_plot(nx, ny, source, x_range=None, output_backend=DEFAULT_BACKEND):
    import pdb; pdb.set_trace()
    # avoid range errors
    if len(source[N.ACTIVE_TIME].dropna()) < 2:
        return None
    groups = [group for statistic, group in related_statistics(source, N.ACTIVE_TIME)]
    if not groups:
        # original monochrome plot
        return multi_dot_plot(nx, ny, N.TIME, [N.ACTIVE_TIME_H, N.ACTIVE_DISTANCE_KM], source,
                              ['black', 'grey'], alphas=[1, 0.5], x_range=x_range, rescale=True)
    times = [f'{N.ACTIVE_TIME}:{group}' for group in groups]
    distances = [f'{N.ACTIVE_DISTANCE}:{group}' for group in groups]
    time_y_range = make_range(source[N.ACTIVE_TIME_H])
    distance_y_range = make_range(source[N.ACTIVE_DISTANCE_KM])
    colours = list(evenly_spaced_hues(len(groups)))
    tooltip_names = [N.ACTIVE_TIME_H, N.ACTIVE_DISTANCE_KM, N.ACTIVITY_GROUP, N.LOCAL_TIME]
    tooltip_names += [name for name in like(N._delta(N.FITNESS_D_ANY), source.columns) if ':' not in name]
    tooltip_names += [name for name in like(N._delta(N.FATIGUE_D_ANY), source.columns) if ':' not in name]
    tools = [PanTool(dimensions='width'),
             ZoomInTool(dimensions='width'), ZoomOutTool(dimensions='width'),
             ResetTool(),
             HoverTool(tooltips=[tooltip(name) for name in tooltip_names], names=['with_hover'])]
    f = figure(output_backend=output_backend, plot_width=nx, plot_height=ny, x_axis_type='datetime', tools=tools)
    f.yaxis.axis_label = f'lines - {N.ACTIVE_TIME_H}'
    f.y_range = time_y_range
    f.extra_y_ranges = {N.ACTIVE_DISTANCE: distance_y_range}
    f.add_layout(LinearAxis(y_range_name=N.ACTIVE_DISTANCE, axis_label=f'dots - {N.ACTIVE_DISTANCE_KM}'), 'right')
    plotter = comb_plotter()
    for time, colour, group in zip(times, colours, groups):
        time_h = N._slash(time, Units.H)
        source[time_h] = source[time] / 3600
        source[N.ACTIVITY_GROUP] = group
        plotter(f, x=N.TIME, y=time_h, source=source, color=colour, alpha=1)
    plotter = dot_plotter()
    for distance, colour, group in zip(distances, colours, groups):
        distance_km = N._slash(distance, Units.KM)
        source[distance_km] = source[distance] / 1000
        source[N.ACTIVITY_GROUP] = group
        plotter(f, x=N.TIME, y=distance_km, source=source, color=colour, alpha=1, name='with_hover',
                y_range_name=N.ACTIVE_DISTANCE)
    f.xaxis.axis_label = N.TIME
    f.toolbar.logo = None
    if ny < 300: f.toolbar_location = None
    if x_range: f.x_range = x_range
    return f
