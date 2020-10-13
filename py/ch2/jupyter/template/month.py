
import datetime as dt
from calendar import day_name, Calendar

from bokeh.io import output_file
from bokeh.layouts import column, grid
from bokeh.models import Div, Spacer
from bokeh.plotting import show

from ch2.data import *
from ch2.jupyter.decorator import template
from ch2.lib import to_date, local_date_to_time, format_seconds, format_km
from ch2.names import N
from ch2.pipeline.owners import *
from ch2.sql import ActivityJournal


@template
def month(month):

    f'''
    # Month: {month}
    '''

    '''
    $contents
    '''

    '''
    ## Preparation
    '''
    
    s = session('-v2')
    output_file(filename='/dev/null')
    map_size = 100
    month_start = to_date(month).replace(day=1)

    '''
    ## Generate Plot
    '''

    def days():

        for i in Calendar().iterweekdays():
            yield Div(text=f'<h2>{day_name[i]}</h2>')

        day = month_start - dt.timedelta(days=month_start.weekday())
        while day.month <= month_start.month:
            for weekday in range(7):
                if day.month == month_start.month:
                    contents = [Div(text=f'<h1>{day.strftime("%d")}</h1>')]
                    for a in s.query(ActivityJournal). \
                            filter(ActivityJournal.start >= local_date_to_time(day),
                                   ActivityJournal.start < local_date_to_time(day + dt.timedelta(days=1))).all():
                        df = Statistics(s, activity_journal=a). \
                            by_name(ActivityReader, N.SPHERICAL_MERCATOR_X, N.SPHERICAL_MERCATOR_Y).df
                        contents.append(map_thumbnail(map_size, map_size, df, title=False))
                        df = Statistics(s, activity_journal=a). \
                            by_name(ActivityCalculator, N.ACTIVE_DISTANCE, N.ACTIVE_TIME).df
                        contents.append(Div(
                            text=f'{format_km(df[N.ACTIVE_DISTANCE][0])} {format_seconds(df[N.ACTIVE_TIME][0])}'))
                else:
                    contents = [Spacer()]
                yield column(contents)
                day += dt.timedelta(days=1)

    show(grid(list(days()), ncols=7))
