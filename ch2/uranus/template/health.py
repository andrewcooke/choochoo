
import datetime as dt

from bokeh.io import output_file
from bokeh.layouts import column
from bokeh.plotting import show

from ch2.data import *
from ch2.uranus.decorator import template


@template
def health(local_time):

    f'''
    # Health: {local_time.split()[0]}
    '''

    '''
    $contents
    '''

    '''
    ## Load Data
    
    Open a connection to the database and load the data we require.
    '''

    s = session('-v2')
    health = std_health_statistics(s)

    '''
    ## Health and Fitness
    '''

    output_file(filename='/dev/null')

    ff = multi_line_plot(900, 300, TIME, [FITNESS, FATIGUE], health, ['black', 'red'], alphas=[1, 0.3])
    log_ff = multi_line_plot(900, 100, TIME, [LOG_FITNESS, LOG_FATIGUE], health, ['black', 'red'], alphas=[1, 0.5],
                             x_range=ff.x_range, y_label='Log FF')
    atd = multi_dot_plot(900, 200, TIME, [ACTIVE_TIME_H, ACTIVE_DISTANCE_KM], health, ['black', 'grey'], alphas=[1, 0.5],
                         x_range=ff.x_range, rescale=True)
    shr = multi_plot(900, 200, TIME, [DAILY_STEPS, REST_HR], health, ['grey', 'red'], alphas=[1, 0.5],
                     x_range=ff.x_range, rescale=True, plotters=[bar_plotter(dt.timedelta(hours=20)), dot_plotter()])
    show(column(ff, log_ff, atd, shr))
