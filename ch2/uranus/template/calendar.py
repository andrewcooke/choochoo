
from bokeh.io import output_file
from bokeh.palettes import magma
from bokeh.plotting import show

from ch2.data import *
from ch2.lib import format_seconds
from ch2.uranus.decorator import template


@template
def calendar():

    '''
    # Calendar
    '''

    '''
    $contents
    '''

    s = session('-v5')
    output_file(filename='/dev/null')

    '''
    ## Distance

    Larger distances have larger symbols.
    
    Place the cursor over the symbol for more information.
    '''

    df = statistics(s, ACTIVE_DISTANCE, ACTIVE_TIME, TOTAL_CLIMB)
    df[DISTANCE_KM] = df[ACTIVE_DISTANCE] / 1000
    df['Duration'] = df[ACTIVE_TIME].map(format_seconds)
    df.loc[df[TOTAL_CLIMB].isna(), [TOTAL_CLIMB]] = 0

    calendar_size(df, ACTIVE_DISTANCE, min=0.1, gamma=0.5)
    p = calendar_plot(df, title='Distance and Time', fill='black',
                      hover=(DISTANCE_KM, 'Duration', TOTAL_CLIMB, LOCAL_TIME))

    show(p)

    '''
    ## Distance and Climb

    Larger distances have larger symbols.  Higher climbs have "hotter" colours.
    
    Place the cursor over the symbol for more information.
    '''

    calendar_size(df, ACTIVE_DISTANCE, min=0.1, gamma=0.5)
    calendar_color(df, TOTAL_CLIMB, magma(256))
    p = calendar_plot(df, title='Distance and Climb', background='fill',
                      hover=(DISTANCE_KM, 'Duration', TOTAL_CLIMB, LOCAL_TIME))

    show(p)

    '''
    ## Fitness and Fatigue

    Better fitness has larger symbols.  When fatigue is higher symbols have "hotter" colours.
    
    Place the cursor over the symbol for more information.
    '''

    df = statistics(s, FITNESS_D_ANY, FATIGUE_D_ANY)
    df = df.resample('1D').mean()
    # take shortest period values when multiple definitions
    fitness = sorted(col for col in df.columns if col.startswith(FITNESS))[0]
    fatigue = sorted(col for col in df.columns if col.startswith(FATIGUE))[0]
    df['FF Ratio'] = df[fatigue] / df[fitness]
    calendar_size(df, fitness, min=0.1, gamma=0.5)
    calendar_color(df, 'FF Ratio', magma(256), lo=0.5, hi=2, min=0)
    p = calendar_plot(df, title='Fitness and Fatigue', background=None, border_month=0)

    show(p)
