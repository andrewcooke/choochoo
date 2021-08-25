
import datetime as dt

from bokeh.io import output_file
from bokeh.layouts import gridplot
from bokeh.plotting import show

from ch2.data import *
from ch2.jupyter.decorator import template
from ch2.names import Names as N, like


@template
def health():

    '''
    # Health
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

    fitness, fatigue = like(N.FITNESS_ANY, health.columns), like(N.FATIGUE_ANY, health.columns)
    colours = ['black'] * len(fitness) + ['red'] * len(fatigue)
    alphas = [1.0] * len(fitness) + [0.5] * len(fatigue)
    ff = multi_line_plot(900, 300, N.TIME, fitness + fatigue, health, colours, alphas=alphas)
    xrange = ff.x_range if ff else None
    add_multi_line_at_index(ff, N.TIME, fitness + fatigue, health, colours, alphas=alphas, index=-1)
    atd = std_distance_time_plot(900, 200, health, x_range=xrange)
    show(gridplot([[ff], [atd]]))
