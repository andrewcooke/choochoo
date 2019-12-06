
from operator import add

from bokeh.models import GMapOptions
from bokeh.plotting import show, gmap

from ch2.data import *
from ch2.data.plot import DEFAULT_BACKEND
from ch2.jupyter.decorator import template
from ch2.lib import *
from ch2.sql import *


@template
def gmap_activities(start, finish, activity_group_name, google_key):

    f'''
    # Google Maps Activities: {start.split()[0]} - {finish.split()[0]} / {activity_group_name}
    '''

    '''
    $contents
    '''

    '''
    ## Read Data
    '''

    s = session('-v2')
    data_frames = [activity_statistics(s, LATITUDE, LONGITUDE, activity_journal=aj)
                   for aj in s.query(ActivityJournal).
                       filter(ActivityJournal.start >= local_date_to_time(start),
                              ActivityJournal.start < local_date_to_time(finish),
                              ActivityJournal.activity_group == ActivityGroup.from_name(s, activity_group_name)).
                       all()]
    data_frames = [data_frame.dropna() for data_frame in data_frames if not data_frame.dropna().empty]
    print(f'Found {len(data_frames)} activities')

    '''
    ## Calculate Centre
    '''

    ll = [(data_frame[LATITUDE].mean(), data_frame[LONGITUDE].mean()) for data_frame in data_frames]
    ll = list(zip(*ll))
    ll = (median(ll[0]), median(ll[1]))

    '''
    ## Display
    '''

    map_options = GMapOptions(lat=ll[0], lng=ll[1], map_type="roadmap", scale_control=True)
    f = gmap(google_key, map_options, title=f'{start.split()[0]} - {finish.split()[0]} / {activity_group_name}',
             tools='pan,zoom_in,zoom_out,reset,undo,redo,save', output_backend=DEFAULT_BACKEND)
    for data_frame in data_frames:
        f.line(x=LONGITUDE, y=LATITUDE, source=data_frame)

    show(f)
