
from bokeh.plotting import output_notebook, show

from ch2.data import *
from ch2.uranus.decorator import template


@template
def some_activities(constraint):

    f'''
    # Some Activities: {constraint}

    This displays thumbnails of routes that match the query over statistics.  For example,

        Active Distance > 40000 & Active Distance < 60000

    will show all activities with a distance between 40 and 60 km.
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
                                             ACTIVE_DISTANCE, TOTAL_CLIMB,
                                             activity_journal=aj)
                         for aj in constrained_activities(s, constraint))
            if len(data[SPHERICAL_MERCATOR_X].dropna()) > 10]
    print(f'Found {len(maps)} activities')

    '''
    ## Display Maps
    '''

    output_notebook()
    show(htile(maps, 8))
