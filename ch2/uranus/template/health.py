
import datetime as dt

from bokeh.io import output_file
from bokeh.layouts import column
from bokeh.plotting import show

from ch2.data import *
from ch2.lib import to_date
from ch2.stoats.names import _log
from ch2.uranus.decorator import template


@template
def health(local_time: to_date):  # todo - date not used?

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

    fitness, fatigue = like(FITNESS_D_ANY, health.columns), like(FATIGUE_D_ANY, health.columns)
    colours = ['black'] * len(fitness) + ['red'] * len(fatigue)
    alphas = [1.0] * len(fitness) + [0.5] * len(fatigue)
    ff = multi_line_plot(900, 300, TIME, fitness + fatigue, health, colours, alphas=alphas)
    log_ff = multi_line_plot(900, 100, TIME, [_log(name) for name in fitness + fatigue], health, colours,
                             alphas=alphas, x_range=ff.x_range, y_label='Log FF')
    atd = multi_dot_plot(900, 200, TIME, [ACTIVE_TIME_H, ACTIVE_DISTANCE_KM], health, ['black', 'grey'], alphas=[1, 0.5],
                         x_range=ff.x_range, rescale=True)
    shr = multi_plot(900, 200, TIME, [DAILY_STEPS, REST_HR], health, ['grey', 'red'], alphas=[1, 0.5],
                     x_range=ff.x_range, rescale=True, plotters=[bar_plotter(dt.timedelta(hours=20)), dot_plotter()])
    show(column(ff, log_ff, atd, shr))
