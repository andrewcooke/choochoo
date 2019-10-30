
import datetime as dt

from IPython.core.display import display
from bokeh.io import output_file
from bokeh.layouts import row, column, gridplot
from bokeh.plotting import show

from ch2.data import *
from ch2.lib import *
from ch2.stoats.names import _log
from ch2.uranus.decorator import template


@template
def activity_details(local_time, activity_group_name):

    f'''
    # Activity Details: {local_time.split()[0]} ({activity_group_name})
    '''

    '''
    $contents
    '''

    '''
    ## Load Data
    
    Open a connection to the database and load the data we require.
    '''

    s = session('-v2')

    activity = std_activity_statistics(s, local_time=local_time, activity_group_name=activity_group_name)
    details = activity_statistics(s, 'Climb %', ACTIVE_TIME, ACTIVE_DISTANCE, local_time=local_time,
                                  activity_group_name=activity_group_name)
    health = std_health_statistics(s)
    hr_zones = hr_zones_from_database(s, local_time, activity_group_name)

    f'''
    ## Activity Plots
    
    To the right of each plot of data against distance is a related plot of cumulative data
    (except the last, cadence, which isn't useful and so replaced by HR zones).
    Green and red areas indicate differences between the two dates. 
    Additional red lines on the altitude plot are auto-detected climbs.
    
    Plot tools support zoom, dragging, etc.
    '''

    output_file(filename='/dev/null')

    sp = comparison_line_plot(700, 200, DISTANCE_KM, MED_SPEED_KMH, activity, ylo=0)
    sp_c = cumulative_plot(200, 200, MED_SPEED_KMH, activity, ylo=0)

    el = comparison_line_plot(700, 200, DISTANCE_KM, ELEVATION_M, activity, x_range=sp.x_range)
    add_climbs(el, details, activity)
    el_c = cumulative_plot(200, 200, CLIMB_MS, activity)

    hri = comparison_line_plot(700, 200, DISTANCE_KM, HR_IMPULSE_10, activity, ylo=0, x_range=sp.x_range)
    hri_c = cumulative_plot(200, 200, HR_IMPULSE_10, activity, ylo=0)

    hr = comparison_line_plot(700, 200, DISTANCE_KM, HEART_RATE_BPM, activity, x_range=sp.x_range)
    add_hr_zones(hr, activity, DISTANCE_KM, hr_zones)
    hr_c = cumulative_plot(200, 200, HEART_RATE_BPM, activity)

    pw = comparison_line_plot(700, 200, DISTANCE_KM, MED_POWER_ESTIMATE_W, activity, ylo=0, x_range=sp.x_range)
    pw_c = cumulative_plot(200, 200, MED_POWER_ESTIMATE_W, activity, ylo=0)

    cd = comparison_line_plot(700, 200, DISTANCE_KM, MED_CADENCE, activity, ylo=0, x_range=sp.x_range)
    hr_h = histogram_plot(200, 200, HR_ZONE, activity, xlo=1, xhi=5)

    show(gridplot([[el, el_c], [sp, sp_c], [hri, hri_c], [hr, hr_c], [pw, pw_c], [cd, hr_h]]))

    '''
    ## Activity Maps
    '''

    map = map_plot(400, 400, activity)
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

    details[[ACTIVE_TIME, ACTIVE_DISTANCE]].dropna(). \
        transform({ACTIVE_TIME: format_seconds, ACTIVE_DISTANCE: format_metres})

    '''
    Climbs are auto-detected and shown only for the main activity. They are included in the elevation plot above.
    '''

    if present(details, CLIMB_TIME):
        display(transform(details.filter(like='Climb').dropna(),
                          {CLIMB_TIME: format_seconds, CLIMB_ELEVATION: format_metres,
                           CLIMB_DISTANCE: format_metres, CLIMB_GRADIENT: format_percent,
                           CLIMB_POWER: format_watts, CLIMB_CATEGORY: lambda x: x}))

    '''
    ## Health and Fitness
    '''

    fitness, fatigue = like(FITNESS_D_ANY, health.columns), like(FATIGUE_D_ANY, health.columns)
    colours = ['black'] * len(fitness) + ['red'] * len(fatigue)
    alphas = [1.0] * len(fitness) + [0.5] * len(fatigue)
    ff = multi_line_plot(900, 300, TIME, fitness + fatigue, health, colours, alphas=alphas)
    xrange = ff.x_range if ff else None
    log_ff = multi_line_plot(900, 100, TIME, [_log(name) for name in fitness + fatigue], health, colours,
                             alphas=alphas, x_range=xrange, y_label='Log FF')
    add_multi_line_at_index(ff, TIME, fitness + fatigue, health, colours, alphas=alphas, index=-1)
    atd = std_distance_time_plot(900, 200, health, x_range=ff.x_range)
    shr = multi_plot(900, 200, TIME, [DAILY_STEPS, REST_HR], health, ['grey', 'red'], alphas=[1, 0.5],
                     x_range=xrange, rescale=True, plotters=[bar_plotter(dt.timedelta(hours=20)), dot_plotter()])
    add_band(shr, TIME, LO_REST_HR, HI_REST_HR, health, 'red', alpha=0.1, y_range_name=REST_HR)
    show(column(ff, log_ff, atd, shr))
