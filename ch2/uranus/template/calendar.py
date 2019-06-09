
from bokeh.io import output_file
from bokeh.palettes import magma

from ch2.data import *
from ch2.data.plot.calendar import *
from ch2.lib import *
from ch2.stoats.names import _d
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
    df = coallesce(df, ACTIVE_DISTANCE, ACTIVE_TIME, TOTAL_CLIMB)
    df[DISTANCE_KM] = df[ACTIVE_DISTANCE] / 1000
    df['Duration'] = df[ACTIVE_TIME].map(format_seconds)
    if present(df, TOTAL_CLIMB):
        df.loc[df[TOTAL_CLIMB].isna(), [TOTAL_CLIMB]] = 0

    calendar = Calendar(df, title=DISTANCE, not_hover=[ACTIVE_DISTANCE, ACTIVE_TIME])
    calendar.std_distance()

    '''
    ## Work Done and Fatigue

    Larger increases in Fitness have larger symbols.  Higher fatigue is redder.
    
    Place the cursor over the symbol for more information.
    '''

    df1 = statistics(s, ACTIVE_DISTANCE, ACTIVE_TIME, TOTAL_CLIMB, _d(FITNESS_D_ANY))
    if present(df1, _d(FITNESS_D_ANY), pattern=True):
        df1 = coallesce(df1, ACTIVE_DISTANCE, ACTIVE_TIME, TOTAL_CLIMB)
        if present(df, TOTAL_CLIMB):
            df1.loc[df1[TOTAL_CLIMB].isna(), [TOTAL_CLIMB]] = 0  # before interpolation
        df2 = statistics(s, FATIGUE_D_ANY, FITNESS_D_ANY)
        df = left_interpolate(df1, df2)
        df[DISTANCE_KM] = df[ACTIVE_DISTANCE] / 1000
        df['Duration'] = df[ACTIVE_TIME].map(format_seconds)
        work_done = sorted_numeric_labels(df.columns, FITNESS)[0]
        fitness = sorted_numeric_labels(df2.columns, FITNESS)[0]
        fatigue = sorted_numeric_labels(df2.columns, FATIGUE)[0]
        print(fatigue, fitness)
        df['FF Ratio'] = df[fatigue] / df[fitness]

        calendar = Calendar(df, title='Work Done and Fatigue', not_hover=[ACTIVE_DISTANCE, ACTIVE_TIME])
        calendar.background('square', fill_alpha=0, line_alpha=1, color='lightgrey')
        calendar.set_palette('FF Ratio', K2R, lo=0.5, hi=2)
        calendar.set_size(work_done, min=0.1, gamma=0.5)
        calendar.foreground('square', fill_alpha=1, line_alpha=0)
        calendar.show()

    '''
    ## Distance, Climb and Direction

    Larger distances have larger symbols.  Higher climbs are redder.  
    The arc indicates the general direction relative to the start.
    
    Place the cursor over the symbol for more information.
    '''

    df = statistics(s, ACTIVE_DISTANCE, ACTIVE_TIME, TOTAL_CLIMB, DIRECTION, ASPECT_RATIO)
    df = coallesce(df, ACTIVE_DISTANCE, ACTIVE_TIME, TOTAL_CLIMB, DIRECTION, ASPECT_RATIO)
    df[DISTANCE_KM] = df[ACTIVE_DISTANCE] / 1000
    df['Duration'] = df[ACTIVE_TIME].map(format_seconds)
    if present(df, TOTAL_CLIMB):
        df.loc[df[TOTAL_CLIMB].isna(), TOTAL_CLIMB] = 0

    calendar = Calendar(df, title='Distance, Climb and Direction', not_hover=[ACTIVE_DISTANCE, ACTIVE_TIME])
    calendar.std_distance_climb_direction()

    '''
    ## Distance, Work Done and Direction

    Larger distances have larger symbols.  Larger gains in fitness are redder.  
    The arc indicates the general direction relative to the start.
    
    Place the cursor over the symbol for more information.
    '''

    df = statistics(s, ACTIVE_DISTANCE, ACTIVE_TIME, TOTAL_CLIMB, DIRECTION, ASPECT_RATIO, _d(FITNESS_D_ANY))
    if present(df, _d(FITNESS_D_ANY), pattern=True):
        df = coallesce(df, ACTIVE_DISTANCE, ACTIVE_TIME, TOTAL_CLIMB, DIRECTION, ASPECT_RATIO)
        df[DISTANCE_KM] = df[ACTIVE_DISTANCE] / 1000
        df['Duration'] = df[ACTIVE_TIME].map(format_seconds)
        if present(df, TOTAL_CLIMB):
            df.loc[df[TOTAL_CLIMB].isna(), TOTAL_CLIMB] = 0

        calendar = Calendar(df, title='Distance, Fitness and Direction', not_hover=[ACTIVE_DISTANCE, ACTIVE_TIME])
        calendar.std_distance_fitness_direction()

    '''
    ## Fitness and Fatigue

    Better fitness has larger symbols.  When fatigue is higher symbols have "hotter" colours.
    
    Place the cursor over the symbol for more information.
    '''

    # avoid throwing an exception if missing; plot skipped on next line
    df = statistics(s, FITNESS_D_ANY, FATIGUE_D_ANY, check=False)
    if present(df, FITNESS_D_ANY, pattern=True):
        df = df.resample('1D').mean()
        # take shortest period values when multiple definitions
        fitness = sorted_numeric_labels(df.columns, FITNESS)[0]
        fatigue = sorted_numeric_labels(df.columns, FATIGUE)[0]
        df['FF Ratio'] = df[fatigue] / df[fitness]

        calendar = Calendar(df, title='Fitness and Fatigue', scale=18, border_month=0, border_day=0)
        calendar.set_size(fitness, min=0.1, gamma=0.5)
        calendar.set_palette('FF Ratio', magma(256), lo=0.5, hi=2, min=0)
        calendar.foreground('square', fill_alpha=1, line_alpha=0)
        calendar.show()

    '''
    ## Groups, Distance, Climb and Direction

    Larger distances have larger symbols.  Higher climbs are lighter.  
    The arc indicates the general direction relative to the start.
    Pastel backgrounds group similar rides.
    
    Place the cursor over the symbol for more information.
    '''

    dfa = statistics(s, ACTIVE_DISTANCE, ACTIVE_TIME, TOTAL_CLIMB, DIRECTION, ASPECT_RATIO)
    dfa = coallesce(dfa, ACTIVE_DISTANCE, ACTIVE_TIME, TOTAL_CLIMB, DIRECTION, ASPECT_RATIO)
    dfa[DISTANCE_KM] = dfa[ACTIVE_DISTANCE] / 1000
    dfa['Duration'] = dfa[ACTIVE_TIME].map(format_seconds)
    if present(dfa, TOTAL_CLIMB):
        dfa.loc[dfa[TOTAL_CLIMB].isna(), TOTAL_CLIMB] = 0
    dfb = groups_by_time(s)
    if present(dfb, GROUP):
        dfb.loc[dfb[GROUP].isna(), GROUP] = -1
        df = dfa.join(dfb)

        calendar = Calendar(df, not_hover=[ACTIVE_DISTANCE, ACTIVE_TIME], scale=15, border_day=0.1)
        calendar.std_group_distance_climb_direction()
