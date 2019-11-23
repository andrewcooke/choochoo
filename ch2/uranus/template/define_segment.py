
from bokeh import tile_providers
from bokeh.io import output_file
from bokeh.layouts import row, column
from bokeh.models import PreText, Slider
from bokeh.plotting import show, figure

from ch2.data import *
from ch2.squeal import Segment
from ch2.uranus.decorator import template


@template
def define_segment(local_time):

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
    df = activity_statistics(s, SPHERICAL_MERCATOR_X, SPHERICAL_MERCATOR_Y, DISTANCE, ELEVATION,
                             LATITUDE, LONGITUDE, local_time=local_time)
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
        map = figure(plot_width=width, plot_height=height, x_axis_type='mercator', y_axis_type='mercator',
                     match_aspect=True)
        map.add_tile(TILE)
        map.circle(x=SPHERICAL_MERCATOR_X, y=SPHERICAL_MERCATOR_Y, source=df, name='map')
        elevation = figure(plot_width=width, plot_height=height//10)
        elevation.line(x=DISTANCE, y=ELEVATION, source=df, name='elevation')
        c = column(row(s1, s2), row(t1, t2, t3), map, elevation)

        def mkplot(l1, l2):
            l2 = min(len(df)-1, l1+l2)
            t1.text = '%9.5f,%9.5f' % (df.iloc[l1]['Longitude'], df.iloc[l1]['Latitude'])
            t2.text = '%9.5f,%9.5f' % (df.iloc[l2]['Longitude'], df.iloc[l2]['Latitude'])
            t3.text = '%4.2fkm' % ((df.iloc[l2]['Distance'] - df.iloc[l1]['Distance']) / 1000)
            get_renderer(map, 'map').data_source.data = df[l1:l2]
            get_renderer(elevation, 'elevation').data_source.data = df[l1:l2]

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

    segment = Segment(start=(-70.61813, -33.41536), finish=(-70.63340, -33.42655), distance=4400,
                      name='San Cristobal', description='Climb up San Cristobal in Parque Metropolitana')
    #s.add(segment)
