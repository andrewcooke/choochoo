
from bokeh.io import output_file
from bokeh.layouts import row, column
from bokeh.plotting import show

from ch2.data import *
from ch2.uranus.notebook.data import *
from ch2.uranus.notebook.plot import *
from ch2.uranus.template.decorator import template


@template
def compare_activities(activity_date, compare_date, group):

    f'''
    # Compare Activities: {activity_date.split()[0]} v {compare_date.split()[0]}
    '''

    '''
    $contents
    '''

    '''
    ## Load Data
    
    Open a connection to the database and load the data we require.
    '''

    s = session('-v2')

    activity = std_activity_stats(s, time=activity_date, group=group)
    compare = std_activity_stats(s, time=compare_date, group=group)
    details = activity_statistics(s, 'Climb %', ACTIVE_TIME, ACTIVE_DISTANCE, time=activity_date, group=group)
    health = std_health_stats(s)

    f'''
    ## Activity Plots
    
    The black line shows data from {activity_date.split()[0]}, 
    the grey line from {compare_date.split()[0]}. 
    To the right of each plot of data against distance is a related plot of cumulative data
    (except the last, cadence, which isn't useful and so replaced by HR zones).
    Green and red areas indicate differences between the two dates. 
    Additional red lines on the altitude plot are auto-detected climbs.
    
    Plot tools support zoom, dragging, etc.
    '''

    output_file(filename='/dev/null')

    el = comparison_line_plot(700, 200, DISTANCE_KM, ELEVATION_M, activity, other=compare)
    add_climbs(el, details, activity)
    el_c = cumulative_plot(200, 200, CLIMB_MS, activity, other=compare)

    sp = comparison_line_plot(700, 200, DISTANCE_KM, MED_SPEED_KMH, activity, other=compare, ylo=0, x_range=el.x_range)
    sp_c = cumulative_plot(200, 200, MED_SPEED_KMH, activity, other=compare, ylo=0)

    hr = comparison_line_plot(700, 200, DISTANCE_KM, MED_HR_IMPULSE_10, activity, other=compare, ylo=0, x_range=el.x_range)
    hr_c = cumulative_plot(200, 200, MED_HR_IMPULSE_10, activity, other=compare, ylo=0)

    cd = comparison_line_plot(700, 200, DISTANCE_KM, MED_CADENCE, activity, other=compare, ylo=0, x_range=el.x_range)
    hr_h = histogram_plot(200, 200, HR_ZONE, activity, xlo=1, xhi=5)

    show(column(row(el, el_c), row(sp, sp_c), row(hr, hr_c), row(cd, hr_h)))

    '''
    ## Activity Maps
    '''

    map = map_plot(400, 400, activity, other=compare)
    m_el = map_intensity(200, 200, activity, ELEVATION_M, ranges=map)
    m_sp = map_intensity(200, 200, activity, SPEED_KMH, ranges=map)
    m_hr = map_intensity(200, 200, activity, HR_IMPULSE_10, ranges=map)
    m_cd = map_intensity(200, 200, activity, CADENCE, ranges=map)
    show(row(map, column(row(m_el, m_sp), row(m_hr, m_cd))))

    '''
    ## Activity Statistics
    '''

    '''
    Active time and distance exclude pauses.
    '''

    details[[ACTIVE_TIME, ACTIVE_DISTANCE]].dropna()

    '''
    Climbs are auto-detected and shown only for the main activity. They are included in the elevation plot above.
    '''

    details.filter(like='Climb').dropna()

    '''
    ## Health and Fitness
    '''

    ff = multi_line_plot(900, 300, TIME, [FITNESS, FATIGUE], health, ['black', 'red'], alphas=[1, 0.3])
    log_ff = multi_line_plot(900, 100, TIME, [LOG_FITNESS, LOG_FATIGUE], health, ['black', 'red'], alphas=[1, 0.5],
                             x_range=ff.x_range, y_label='Log FF')
    atd = multi_dot_plot(900, 200, TIME, [ACTIVE_TIME_H, ACTIVE_DISTANCE_KM], health, ['black', 'grey'], alphas=[1, 0.5],
                         x_range=ff.x_range, rescale=True)
    shr = multi_plot(900, 200, TIME, [DAILY_STEPS, REST_HR], health, ['grey', 'red'], alphas=[1, 0.5],
                     x_range=ff.x_range, rescale=True, plotters=[bar_plotter(dt.timedelta(hours=20)), dot_plotter()])
    show(column(ff, log_ff, atd, shr))
