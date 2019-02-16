
from bokeh.layouts import row, column
from bokeh.plotting import output_notebook, show

from ch2.data import *
from ch2.lib.date import local_date_to_time
from ch2.squeal import *
from ch2.uranus.notebook.plot import *
from ch2.uranus.template.decorator import template


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

    maps = [[]]
    for aj in s.query(ActivityJournal). \
            filter(ActivityJournal.start >= local_date_to_time(start),
                   ActivityJournal.start < local_date_to_time(finish)).all():
        data = activity_statistics(s, SPHERICAL_MERCATOR_X, SPHERICAL_MERCATOR_Y,
                                   activity_journal_id=aj.id).resample('1min').mean()
        if len(data.dropna()) > 10:
            map = map_thumbnail(100, 120, data)
            if len(maps[-1]) > 8: maps.append([])
            maps[-1].append(map)

    '''
    ## Display Maps
    '''

    output_notebook()
    show(column([row(m) for m in maps]))
