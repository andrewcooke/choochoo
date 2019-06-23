
from bokeh.plotting import output_notebook, show

from ch2.data import *
from ch2.uranus.decorator import template


@template
def some_activities(constraint):

    f'''
    # Some Activities: {constraint}
    '''

    '''
    $contents
    '''

    '''
    ## Build Maps
    
    Loop over activities, retrieve data, and construct maps. 
    '''

    s = session('-v2')
    maps = [map_thumbnail(100, 120, data.resample('1min').mean())
            for data in (activity_statistics(s, SPHERICAL_MERCATOR_X, SPHERICAL_MERCATOR_Y,
                                             activity_journal=aj)
                         for aj in constrained_activities(s, constraint))
            if len(data.dropna()) > 10]
    print(f'Found {len(maps)} activities')

    '''
    ## Display Maps
    '''

    output_notebook()
    show(tile(maps, 8))
