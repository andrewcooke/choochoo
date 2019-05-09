
from bokeh.plotting import output_notebook, show

from ch2.data import *
from ch2.lib import *
from ch2.uranus.decorator import template


@template
def similar_activities(local_time: to_date, activity_group_name):

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
            for data in (activity_statistics(s, SPHERICAL_MERCATOR_X, SPHERICAL_MERCATOR_Y,
                                             activity_journal_id=similar[0].id).resample('1min').mean()
                         for similar in nearby_activities(s, local_time=local_time,
                                                          activity_group_name=activity_group_name))
            if len(data.dropna()) > 10]

    print(f'Found {len(maps)} activities')

    '''
    ## Display Maps
    '''

    output_notebook()
    show(tile(maps, 8))
