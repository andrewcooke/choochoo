
from bokeh.layouts import row, column
from bokeh.plotting import output_notebook, show

from ch2.data import *
from ch2.uranus.notebook.data import *
from ch2.uranus.notebook.plot import *


def template(activity_date, compare_date):

    f'''
    # Compare Activities: {activity_date.split()[0]} v {compare_date.split()[0]}
    '''

    '''
    $contents
    '''

    '''
    ## Load Data
    
    Import packages, open connection to database, and load the data we require.
    '''

    s = session('-v2')

    activity = std_activity_stats(s, time=activity_date)
    compare = std_activity_stats(s, time=compare_date)
    climbs = activity_statistics(s, 'Climb %', time=activity_date)
    health = std_health_stats(s)

    '''
    ## Activity Plots
    
    The black line shows data from 2018-03-04, the grey line from 2017-09-19.  
    To the right of each plot of data against distance is a related plot of cumulative data
    (except the last, cadence, which isn't useful and so replaced by HR zones).
    Green and red areas indicate differences between the two dates.  
    Additional red lines on the altitude plot are auto-detected climbs.
    
    Plot tools support zoom, dragging, etc.
    '''

    output_notebook()

    el = comparison_line_plot(700, 200, DISTANCE_KM, ELEVATION_M, activity, other=compare)
    add_climbs(el, climbs, activity)
    el_c = cumulative_plot(150, 200, CLIMB_MS, activity, other=compare)

    hr = comparison_line_plot(700, 200, DISTANCE_KM, MED_HR_IMPULSE_10, activity, other=compare, ylo=0, x_range=el.x_range)
    hr_c = cumulative_plot(150, 200, MED_HR_IMPULSE_10, activity, other=compare, ylo=0)

    sp = comparison_line_plot(700, 200, DISTANCE_KM, MED_SPEED_KMH, activity, other=compare, ylo=0, x_range=el.x_range)
    sp_c = cumulative_plot(150, 200, MED_SPEED_KMH, activity, other=compare, ylo=0)

    show(column(row(el, el_c), row(hr, hr_c), row(sp, sp_c)))

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
    ## Activity Climbs
    
    These are auto-detected and shown only for the main activity.  They are included in the elevation plot above.
    
    todo - Details of how to change parameters?
    '''

    print(climbs)

    '''
    ## Health and Fitness
    '''



    '''
    ## todo
    
    Active distance, time, etc.  Change to using activity journal IDs?
    '''