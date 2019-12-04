
from bokeh.plotting import output_file, show

from ch2.data import *
from ch2.lib import *
from ch2.jupyter.decorator import template


@template
def similar_activities(local_time, activity_group_name):

    f'''
    # Similar Activities: {local_time.split()[0]} ({activity_group_name})
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
            for data in (activity_statistics(s, SPHERICAL_MERCATOR_X, SPHERICAL_MERCATOR_Y,
                                             ACTIVE_DISTANCE, ACTIVE_TIME,
                                             activity_journal=similar[0])
                         for similar in nearby_activities(s, local_time=local_time,
                                                          activity_group_name=activity_group_name))
            if len(data[SPHERICAL_MERCATOR_X].dropna()) > 10]

    print(f'Found {len(maps)} activities')

    '''
    ## Display Maps
    '''

    output_file(filename='/dev/null')
    show(htile(maps, 8))
