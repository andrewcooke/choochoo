
from bokeh.plotting import output_notebook, show
from sqlalchemy import or_, desc

from ch2.data import *
from ch2.lib.date import local_time_to_time
from ch2.squeal import *
from ch2.uranus.decorator import template
from ch2.uranus.notebook.plot import *


@template
def similar_activities(activity_time, group):

    f'''
    # Similar Activities: {activity_time.split()[0]}
    '''

    '''
    $contents
    '''

    '''
    ## Build Maps
    
    Loop over activities, retrieve data, and construct maps. 
    '''

    s = session('-v2')

    activity = s.query(ActivityJournal). \
        join(ActivityGroup). \
        filter(ActivityJournal.start == local_time_to_time(activity_time),
               ActivityGroup.name == group).one()
    maps = [map_thumbnail(100, 120, data)
            for data in (activity_statistics(s, SPHERICAL_MERCATOR_X, SPHERICAL_MERCATOR_Y,
                                             activity_journal_id=s1 if s1 != activity.id else s2)
                             .resample('1min').mean()
                         for s1, s2 in s.query(ActivitySimilarity.activity_journal_lo_id,
                                               ActivitySimilarity.activity_journal_hi_id).
                             filter(or_(ActivitySimilarity.activity_journal_hi == activity,
                                        ActivitySimilarity.activity_journal_lo == activity),
                                    ActivitySimilarity.similarity > 0.5).
                             order_by(desc(ActivitySimilarity.similarity)).all())
            if len(data.dropna()) > 10]
    print(f'Found {len(maps)} activities')

    '''
    ## Display Maps
    '''

    output_notebook()
    show(tile(maps, 8))
