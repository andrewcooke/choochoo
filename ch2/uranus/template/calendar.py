
from bokeh.io import output_file
from bokeh.palettes import magma

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

    df1 = statistics(s, ACTIVE_DISTANCE, ACTIVE_TIME, TOTAL_CLIMB)
    df1[DISTANCE_KM] = df1[ACTIVE_DISTANCE] / 1000
    df1['Duration'] = df1[ACTIVE_TIME].map(format_seconds)
    df1.loc[df1[TOTAL_CLIMB].isna(), [TOTAL_CLIMB]] = 0

    calendar = Calendar(df1, title=DISTANCE, not_hover=[ACTIVE_DISTANCE, ACTIVE_TIME])
    calendar.std_distance()

    '''
    ## Distance and Climb

    Larger distances have larger symbols.  Higher climbs have "hotter" colours.
    
    Place the cursor over the symbol for more information.
    '''

    df2 = statistics(s, ACTIVE_DISTANCE, ACTIVE_TIME, TOTAL_CLIMB, DIRECTION, ASPECT_RATIO)
    df2[DISTANCE_KM] = df2[ACTIVE_DISTANCE] / 1000
    df2['Duration'] = df2[ACTIVE_TIME].map(format_seconds)
    df2.loc[df2[TOTAL_CLIMB].isna(), TOTAL_CLIMB] = 0

    calendar = Calendar(df2, title='Distance and Climb', not_hover=[ACTIVE_DISTANCE, ACTIVE_TIME])
    calendar.std_summary()

    '''
    Square arcs don't look as good.
    '''

    calendar = Calendar(df2, title='Distance and Climb', not_hover=[ACTIVE_DISTANCE, ACTIVE_TIME])
    calendar.background('square', fill_alpha=1, line_alpha=0, color='#F0F0F0')
    calendar.set_size(ACTIVE_DISTANCE, min=0.2, max=1.0)
    calendar.set_palette(TOTAL_CLIMB, magma(256))
    calendar.foreground('square', fill_alpha=1, line_alpha=0)
    calendar.foreground('square', fill_alpha=0, line_alpha=1, color='grey')
    calendar.set_arc(DIRECTION, ASPECT_RATIO, delta_radius=0.15)
    calendar.foreground('sqarc', fill_alpha=0, line_alpha=1, color='black')
    calendar.show()

    '''
    ## Fitness and Fatigue

    Better fitness has larger symbols.  When fatigue is higher symbols have "hotter" colours.
    
    Place the cursor over the symbol for more information.
    '''

    df3 = statistics(s, FITNESS_D_ANY, FATIGUE_D_ANY)
    df3 = df3.resample('1D').mean()
    # take shortest period values when multiple definitions
    fitness = sorted(col for col in df3.columns if col.startswith(FITNESS))[0]
    fatigue = sorted(col for col in df3.columns if col.startswith(FATIGUE))[0]
    df3['FF Ratio'] = df3[fatigue] / df3[fitness]

    calendar = Calendar(df3, title='Fitness and Fatigue', border_month=0, border_day=0)
    calendar.set_size(fitness, min=0.1, gamma=0.5)
    calendar.set_palette('FF Ratio', magma(256), lo=0.5, hi=2, min=0)
    calendar.foreground('square', fill_alpha=1, line_alpha=1)
    calendar.show()
