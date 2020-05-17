
from bokeh.plotting import output_notebook, show

from ch2.data import *
from ch2.lib import *
from ch2.pipeline.calculate.activity import ActivityCalculator
from ch2.pipeline.read.segment import SegmentReader
from ch2.sql import *
from ch2.jupyter.decorator import template


@template
def all_activities(start, finish):

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
    maps = [map_thumbnail(100, 120, data)
            for data in (Statistics(s, aj.activity_group).
                             for_(Names.SPHERICAL_MERCATOR_X, Names.SPHERICAL_MERCATOR_Y, owner=SegmentReader).
                             for_(Names.ACTIVE_DISTANCE, Names.ACTIVE_TIME, owner=ActivityCalculator).
                             from_(activity_journal=aj).by_name().df
                         for aj in s.query(ActivityJournal).
                             filter(ActivityJournal.start >= local_date_to_time(start),
                                    ActivityJournal.start < local_date_to_time(finish)).
                             order_by(ActivityJournal.start.desc()).all())
            if len(data[Names.SPHERICAL_MERCATOR_X].dropna()) > 10]
    print(f'Found {len(maps)} activities')

    '''
    ## Display Maps
    '''

    output_notebook()
    show(htile(maps, 8))
