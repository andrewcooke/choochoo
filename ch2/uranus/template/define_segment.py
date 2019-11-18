
from bokeh import tile_providers
from bokeh.io import output_file
from bokeh.layouts import row, column
from bokeh.models import PreText, Slider
from bokeh.plotting import show, figure

from ch2.data import *
from ch2.squeal import Segment
from ch2.uranus.decorator import template


@template
def define_segment(local_time, activity_group_name):

    f'''
    # Define Segment: {local_time.split()[0]}
    '''

    '''
    $contents
    '''

    '''
    ## Load Data
    
    Open a connection to the database and load the data for a ride containing the segment.
    '''
    s = session('-v2')
    df = activity_statistics(s, SPHERICAL_MERCATOR_X, SPHERICAL_MERCATOR_Y, DISTANCE, LATITUDE, LONGITUDE,
                             local_time=local_time, activity_group_name=activity_group_name)
    df.dropna(inplace=True)
    df.describe()

    '''
    ### Select Segment

    Use the sliders to isolate the segment.
    
    You may need to play with both sliders before the map displays correctly 
    (todo - fix this, and also all the log messages).  
    '''
    TILE = tile_providers.get_provider(tile_providers.Vendors.STAMEN_TERRAIN)

    output_file(filename='/dev/null')
    width, height = 800, 800

    def modify_doc(doc):

        t1 = PreText(height=20, width=200)
        t2 = PreText(height=20, width=200)
        t3 = PreText(height=20, width=100)
        s1 = Slider(start=0, end=len(df), value=0, title='Start')
        s2 = Slider(start=1, end=len(df)-1, value=len(df), title='Length')
        f = figure(plot_width=width, plot_height=height, x_axis_type='mercator', y_axis_type='mercator')
        c = column(row(s1, s2), row(t1, t2, t3), f)

        def mkplot(l1, l2):
            l2 = min(len(df)-1, l1+l2)
            t1.text = '%9.5f,%9.5f' % (df.iloc[l1]['Longitude'], df.iloc[l1]['Latitude'])
            t2.text = '%9.5f,%9.5f' % (df.iloc[l2]['Longitude'], df.iloc[l2]['Latitude'])
            t3.text = '%4.2fkm' % ((df.iloc[l2]['Distance'] - df.iloc[l1]['Distance']) / 1000)
            f = figure(plot_width=width, plot_height=height, x_axis_type='mercator', y_axis_type='mercator')
            f.add_tile(TILE)
            f.circle(x='Spherical Mercator X', y='Spherical Mercator Y', source=df[l1:l2])
            c.children[2] = f

        s1.on_change('value', lambda attr, old, new: mkplot(s1.value, s2.value))
        s2.on_change('value', lambda attr, old, new: mkplot(s1.value, s2.value))
        doc.add_root(c)

    show(modify_doc)

    '''
    ## Define Segment
    
    Replace the details below with your own from the plot above.
    The start and finish values are (lat, lon); the distance is in metres.
    
    Finally, uncomment the `s.add()` to add this to the database.
    '''

    activity_group = ActivityGroup.from_name(s, activity_group_name)
    segment = Segment(start=(-70.61813,-33.41536), finish=(-70.63340,-33.42655), distance=4400,
                      activity_group=activity_group,
                      name='San Cristobal', description='Climb up San Cristobal in Parque Metropolitana')
    #s.add(segment)
