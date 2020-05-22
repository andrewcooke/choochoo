
import datetime as dt

from IPython.core.display import display
from bokeh.io import output_file
from bokeh.layouts import row, gridplot
from bokeh.plotting import show

from ch2.data import *
from ch2.lib import *
from ch2.pipeline.owners import *
from ch2.jupyter.decorator import template


@template
def compare_activities(local_time, compare_time, activity_group):

    f'''
    # Compare Activities: {local_time} v {compare_time} ({activity_group})
    '''

    '''
    $contents
    '''

    '''
    ## Load Data
    
    Open a connection to the database and load the data we require.
    '''

    s = session('-v2')

    activity = std_activity_statistics(s, activity_journal=local_time, activity_group=activity_group)
    compare = std_activity_statistics(s, activity_journal=compare_time, activity_group=activity_group)
    health = std_health_statistics(s)
    hr_zones = hr_zones_from_database(s, local_time, activity_group)
    climbs = Statistics(s, activity_journal=local_time). \
        by_name(ActivityCalculator, N.ACTIVE_TIME, N.ACTIVE_DISTANCE). \
        by_name(ActivityCalculator, N.CLIMB_ANY, like=True).with_. \
        rename_with_units().df

    f'''
    ## Activity Plots
    
    The black line shows data from {local_time}, 
    the grey line from {compare_time}. 
    To the right of each plot of data against distance is a related plot of cumulative data
    (except the last, cadence, which isn't useful and so replaced by HR zones).
    Green and red areas indicate differences between the two dates. 
    Additional red lines on the altitude plot are auto-detected climbs.
    
    Plot tools support zoom, dragging, etc.
    '''

    output_file(filename='/dev/null')

    sp = comparison_line_plot(700, 200, DISTANCE_KM, MED_SPEED_KMH, activity, other=compare, ylo=0)
    add_climb_zones(sp, climbs, activity)
    sp_c = cumulative_plot(200, 200, MED_SPEED_KMH, activity, other=compare, ylo=0)

    el = comparison_line_plot(700, 200, DISTANCE_KM, ELEVATION_M, activity, other=compare, x_range=sp.x_range)
    add_climbs(el, climbs, activity)
    el_c = cumulative_plot(200, 200, CLIMB_MS, activity, other=compare)

    hri = comparison_line_plot(700, 200, DISTANCE_KM, HR_IMPULSE_10, activity, other=compare, ylo=0, x_range=sp.x_range)
    add_climb_zones(hri, climbs, activity)
    hri_c = cumulative_plot(200, 200, HR_IMPULSE_10, activity, other=compare, ylo=0)

    hr = comparison_line_plot(700, 200, DISTANCE_KM, HEART_RATE_BPM, activity, other=compare, x_range=sp.x_range)
    add_hr_zones(hr, activity, DISTANCE_KM, hr_zones)
    add_climb_zones(hr, climbs, activity)
    hr_c = cumulative_plot(200, 200, HEART_RATE_BPM, activity, other=compare)

    pw = comparison_line_plot(700, 200, DISTANCE_KM, MED_POWER_ESTIMATE_W, activity, other=compare, ylo=0, x_range=sp.x_range)
    add_climb_zones(pw, climbs, activity)
    pw_c = cumulative_plot(200, 200, MED_POWER_ESTIMATE_W, activity, other=compare, ylo=0)

    cd = comparison_line_plot(700, 200, DISTANCE_KM, MED_CADENCE, activity, other=compare, ylo=0, x_range=sp.x_range)
    add_climb_zones(cd, climbs, activity)
    hr_h = histogram_plot(200, 200, HR_ZONE, activity, xlo=1, xhi=5)

    show(gridplot([[el, el_c], [sp, sp_c], [hri, hri_c], [hr, hr_c], [pw, pw_c], [cd, hr_h]]))

    '''
    ## Activity Maps
    '''

    map = map_plot(400, 400, activity, other=compare)
    m_el = map_intensity_signed(200, 200, activity, GRADE_PC, ranges=map, power=0.5)
    m_sp = map_intensity(200, 200, activity, SPEED_KMH, ranges=map, power=2)
    m_hr = map_intensity(200, 200, activity, HR_IMPULSE_10, ranges=map)
    m_pw = map_intensity(200, 200, activity, MED_POWER_ESTIMATE_W, ranges=map)
    show(row(map, gridplot([[m_el, m_sp], [m_hr, m_pw]], toolbar_location='right')))

    '''
    ## Activity Statistics
    '''

    '''
    Active time and distance exclude pauses.
    '''

    climbs[[ACTIVE_TIME, ACTIVE_DISTANCE]].dropna(). \
        transform({ACTIVE_TIME: format_seconds, ACTIVE_DISTANCE: format_metres})

    '''
    Climbs are auto-detected and shown only for the main activity. They are included in the elevation plot above.
    '''

    if present(climbs, CLIMB_TIME):
        display(transform(climbs.filter(like='Climb').dropna(),
                          {CLIMB_TIME: format_seconds, CLIMB_ELEVATION: format_metres,
                           CLIMB_DISTANCE: format_km, CLIMB_GRADIENT: format_percent,
                           CLIMB_POWER: format_watts, CLIMB_CATEGORY: lambda x: x}))

    '''
    ## Health and Fitness
    '''

    fitness, fatigue = like(FITNESS_D_ANY, health.columns), like(FATIGUE_D_ANY, health.columns)
    colours = ['black'] * len(fitness) + ['red'] * len(fatigue)
    alphas = [1.0] * len(fitness) + [0.5] * len(fatigue)
    ff = multi_line_plot(900, 300, TIME, fitness + fatigue, health, colours, alphas=alphas)
    xrange = ff.x_range if ff else None
    add_multi_line_at_index(ff, TIME, fitness + fatigue, health, colours, alphas=alphas, index=-1)
    atd = std_distance_time_plot(900, 200, health, x_range=ff.x_range)
    shr = multi_plot(900, 200, TIME, [DAILY_STEPS, REST_HR], health, ['grey', 'red'], alphas=[1, 0.5],
                     x_range=xrange, rescale=True, plotters=[bar_plotter(dt.timedelta(hours=20)), dot_plotter()])
    add_band(shr, TIME, LO_REST_HR, HI_REST_HR, health, 'red', alpha=0.1, y_range_name=REST_HR)
    add_curve(shr, TIME, REST_HR, health, color='red', y_range_name=REST_HR)
    show(gridplot([[ff], [atd], [shr]]))
