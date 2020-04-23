
import rasterio as rio
from matplotlib.pyplot import gca

from ch2.data import *
from ch2.lib.image import write_image, overlay_route, matplot_route, matplot_image
from ch2.msil2a import *
from ch2.msil2a.elevation import create_elevation, add_elevation
from ch2.jupyter.decorator import template


@template
def route_sentinel_3d(user, passwd, local_time, activity_group):

    f'''
    # Route : {local_time} ({activity_group})

    Generate a 3D landscape with the route marked in red.
    The terrain image is taken from Sentinel satellite data.
    The elevation model is calculated from SRTM data (already used to give activity elevation).
    Currently (see below) this cannot be displayed in the notebook, but is saved to file as GeoTIFF data.
    '''

    '''
    $contents
    '''

    '''
    ## Download Image Data
    '''

    s = session('-v2')

    api, products, bbox, df = query_activity(s, user, passwd, local_time, activity_group)
    download_paths = cached_download(s, api, products)

    '''
    ## Create Image
    '''
    image_paths = [create_rgb(download) for download in download_paths]
    images = [rio.open(image) for image in image_paths]
    composite = combine_images(images)
    cropped = crop_to_box(composite, bbox)
    route = overlay_route(cropped, df[LATITUDE].values, df[LONGITUDE].values, (1, 0, 0))

    '''
    ## First Look
    '''

    #%matplotlib notebook
    matplot_image(gca(), route)

    '''
    ## Calculate Elevation
    '''
    dem = create_elevation(s, cropped)
    elevation = add_elevation(route, dem)
    write_image(elevation, '/tmp/route.tiff')

    '''
    ## Display
    
    The file written above contains 4 layers - RGB and elevation.  
    In theory it should be possible to view the 3D image in a GIS tool like qgis.
    In practice it's close, but not quite there.  Hopefully the next version of qgis will fix the issues. 
    
    Originally I hope that myavi would be able to display this image in the notebook, but it appears to be
    largely unmaintained and bit-rotting - I could not get a complete install 
    (with the necessary GUI toolkit needed for full display).
    '''
