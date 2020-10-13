
from bokeh.plotting import output_file, show

from ch2.data import *
from ch2.jupyter.decorator import template
from ch2.names import N
from ch2.pipeline.owners import *


@template
def similar_activities(local_time):

    f'''
    # Similar Activities: {local_time.split()[0]}
    '''

    '''
    $contents
    '''

    '''
    ## Build Maps
    
    Loop over activities, retrieve data, and construct maps. 
    '''

    s = session('-v2')

    maps = [map_thumbnail(100, 120, data)
            for data in (Statistics(s, activity_journal=similar[0]).
                             by_name(ActivityReader, N.SPHERICAL_MERCATOR_X, N.SPHERICAL_MERCATOR_Y).
                             by_name(ActivityCalculator, N.ACTIVE_DISTANCE, N.ACTIVE_TIME).df
                         for similar in nearby_activities(s, local_time=local_time))
            if len(data[N.SPHERICAL_MERCATOR_X].dropna()) > 10]

    print(f'Found {len(maps)} activities')

    '''
    ## Display Maps
    '''

    output_file(filename='/dev/null')
    show(htile(maps, 8))
