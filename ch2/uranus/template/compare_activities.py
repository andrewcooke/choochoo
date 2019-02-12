
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

    activity = std_stats(s, activity_date)
    compare = std_stats(s, compare_date)
    climbs = activity_statistics(s, 'Climb %', time=activity_date)

    '''
    ## Activity Plots
    
    The black line shows data from 2018-03-04, the grey line from 2017-09-19.  
    To the right of each plot of data against distance is a related plot of cumulative data.  
    Green and red areas indicate differences between the two dates.  
    Additional red lines on the altitude plot are auto-detected climbs.
    
    Plot tools support zoom, dragging, etc.
    '''

    output_notebook()

    el = multi_line_plot(700, 200, DISTANCE_KM, ELEVATION_M, activity, other=compare)
    add_climbs(el, climbs, activity)
    el_c = cumulative_plot(150, 200, CLIMB_MS, activity, other=compare)

    hr = multi_line_plot(700, 200, DISTANCE_KM, MED_HR_IMPULSE_10, activity, other=compare, lo=0, x_range=el.x_range)
    hr_c = cumulative_plot(150, 200, MED_HR_IMPULSE_10, activity, other=compare, lo=0)

    sp = multi_line_plot(700, 200, DISTANCE_KM, MED_SPEED_KMH, activity, other=compare, lo=0, x_range=el.x_range)
    sp_c = cumulative_plot(150, 200, MED_SPEED_KMH, activity, other=compare, lo=0)

    show(column(row(el, el_c), row(hr, hr_c), row(sp, sp_c)))
