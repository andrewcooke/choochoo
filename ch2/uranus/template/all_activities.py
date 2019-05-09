
from bokeh.plotting import output_notebook, show

from ch2.data import *
from ch2.lib import *
from ch2.squeal import *
from ch2.uranus.decorator import template


@template
def all_activities(start: to_date, finish: to_date):

    f'''
    # All Activities: {start.split()[0]} - {finish.split()[0]}
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
                         for aj in s.query(ActivityJournal).
                             filter(ActivityJournal.start >= local_date_to_time(start),
                                    ActivityJournal.start < local_date_to_time(finish)).all())
            if len(data.dropna()) > 10]
    print(f'Found {len(maps)} activities')

    '''
    ## Display Maps
    '''

    output_notebook()
    show(tile(maps, 8))
