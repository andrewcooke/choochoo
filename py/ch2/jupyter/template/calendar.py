
from bokeh.io import output_file

from ch2.data import *
from ch2.data.plot.calendar import *
from ch2.jupyter.decorator import template
from ch2.lib import *
from ch2.names import N
from ch2.pipeline.owners import *


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

    df = Statistics(s). \
        by_name(ActivityTopic, N.NAME). \
        by_name(ActivityCalculator, N.ACTIVE_DISTANCE, N.ACTIVE_TIME, N.TOTAL_CLIMB).with_. \
        copy({N.ACTIVE_DISTANCE: N.ACTIVE_DISTANCE_KM}).add_times().df
    df['Duration'] = df[N.ACTIVE_TIME].map(format_seconds)
    if present(df, N.TOTAL_CLIMB):
        df.loc[df[N.TOTAL_CLIMB].isna(), [N.TOTAL_CLIMB]] = 0

    calendar = Calendar(df, title=N.DISTANCE, not_hover=[N.ACTIVE_DISTANCE, N.ACTIVE_TIME])
    calendar.std_distance()

    '''
    ## Work Done and Fatigue

    Larger increases in Fitness have larger symbols.  Higher fatigue (relative to fitness) is redder.
    
    Place the cursor over the symbol for more information.
    '''

    df = Statistics(s). \
        by_name(ActivityTopic, N.NAME). \
        by_name(ActivityCalculator, N.ACTIVE_DISTANCE, N.ACTIVE_TIME, N.TOTAL_CLIMB). \
        by_name(ActivityCalculator, N._delta(N.FITNESS_ANY), like=True).df
    df = Statistics(s). \
        by_name(ResponseCalculator, N.ANY_FATIGUE_ANY, N.ANY_FITNESS_ANY, like=True). \
        with_.drop_prefix(N.DEFAULT).into(df, tolerance='30m')
    df['Duration'] = df[N.ACTIVE_TIME].map(format_seconds)
    df.loc[df[N.TOTAL_CLIMB].isna(), N.TOTAL_CLIMB] = 0
    work_done = sorted_numeric_labels(df.columns, N._delta(N.FITNESS))[0]
    fitness = sorted_numeric_labels(df.columns, N.FITNESS)[0]
    fatigue = sorted_numeric_labels(df.columns, N.FATIGUE)[0]
    print(fatigue, fitness)
    df['FF Ratio'] = df[fatigue] / df[fitness]

    calendar = Calendar(df, title='Work Done and Fatigue',
                        not_hover=[N.ACTIVE_DISTANCE, N.ACTIVE_TIME] +
                                  [column for column in df.columns if ':' in column])
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

    df = Statistics(s). \
        by_name(ActivityTopic, N.NAME). \
        by_name(ActivityCalculator, N.ACTIVE_DISTANCE, N.ACTIVE_TIME, N.TOTAL_CLIMB, N.DIRECTION,
                N.ASPECT_RATIO).df
    df[N.DISTANCE_KM] = df[N.ACTIVE_DISTANCE]
    df['Duration'] = df[N.ACTIVE_TIME].map(format_seconds)
    if present(df, N.TOTAL_CLIMB):
        df.loc[df[N.TOTAL_CLIMB].isna(), N.TOTAL_CLIMB] = 0

    calendar = Calendar(df, title='Distance, Climb and Direction',
                        not_hover=[N.ACTIVE_DISTANCE, N.ACTIVE_TIME] +
                                  [column for column in df.columns if ':' in column])
    calendar.std_distance_climb_direction()

    '''
    ## Distance, Work Done and Direction

    Larger distances have larger symbols.  Larger gains in fitness are redder.  
    The arc indicates the general direction relative to the start.
    
    Place the cursor over the symbol for more information.
    '''

    df = Statistics(s). \
        by_name(ActivityTopic, N.NAME). \
        by_name(ActivityCalculator, N.ACTIVE_DISTANCE, N.ACTIVE_TIME, N.TOTAL_CLIMB, N.DIRECTION,
                N.ASPECT_RATIO). \
        by_name(ActivityCalculator, N._delta(N.FITNESS_ANY), like=True).df
    df[N.DISTANCE_KM] = df[N.ACTIVE_DISTANCE]
    df['Duration'] = df[N.ACTIVE_TIME].map(format_seconds)
    df.loc[df[N.TOTAL_CLIMB].isna(), N.TOTAL_CLIMB] = 0

    calendar = Calendar(df, title='Distance, Fitness and Direction',
                        not_hover=[N.ACTIVE_DISTANCE, N.ACTIVE_TIME] +
                                  [column for column in df.columns if ':' in column])
    calendar.std_distance_fitness_direction()

    '''
    ## Fitness and Fatigue

    Better fitness has larger symbols.  When fatigue is higher symbols have "hotter" colours.
    
    Place the cursor over the symbol for more information.
    '''

    df = Statistics(s). \
        by_name(ActivityTopic, N.NAME). \
        by_name(ActivityCalculator, N.ACTIVE_DISTANCE, N.ACTIVE_TIME). \
        by_name(ActivityCalculator, N._delta(N.FITNESS_ANY), like=True).df
    df = Statistics(s). \
        by_name(ResponseCalculator, N.ANY_FATIGUE_ANY, N.ANY_FITNESS_ANY, like=True). \
        with_.drop_prefix(N.DEFAULT).into(df, tolerance='30m')
    fitness = sorted_numeric_labels(df.columns, N.FITNESS)[0]
    fatigue = sorted_numeric_labels(df.columns, N.FATIGUE)[0]
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

    dfa = Statistics(s). \
        by_name(ActivityTopic, N.NAME). \
        by_name(ActivityCalculator, N.ACTIVE_DISTANCE, N.ACTIVE_TIME, N.TOTAL_CLIMB, N.DIRECTION,
                N.ASPECT_RATIO). \
        by_name(ActivityCalculator, N._delta(N.FITNESS_ANY), like=True).df
    dfa[N.DISTANCE_KM] = df[N.ACTIVE_DISTANCE]
    dfa['Duration'] = df[N.ACTIVE_TIME].map(format_seconds)
    dfa.loc[dfa[N.TOTAL_CLIMB].isna(), N.TOTAL_CLIMB] = 0
    dfb = groups_by_time(s)
    if present(dfb, N.GROUP):
        dfb.loc[dfb[N.GROUP].isna(), N.GROUP] = -1
        df = dfa.join(dfb)

        calendar = Calendar(df, scale=15, border_day=0.1,
                            not_hover=[N.ACTIVE_DISTANCE, N.ACTIVE_TIME] +
                                      [column for column in df.columns if ':' in column])
        calendar.std_group_distance_climb_direction()
