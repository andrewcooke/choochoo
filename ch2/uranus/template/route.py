
import rasterio as rio
from matplotlib.pyplot import gca

from ch2.data import *
from ch2.msil2a import *
from ch2.msil2a.elevation import create_elevation
from ch2.uranus.decorator import template


@template
def route(user, passwd, local_time, activity_group_name):

    f'''
    # Route : {local_time} ({activity_group_name})
    '''

    '''
    $contents
    '''

    '''
    ## Download Image Data
    '''

    redo = False
    s = session('-v2')

    if redo:
        api, products, bbox, df = query_activity(s, user, passwd, local_time, activity_group_name)
        download_paths = cached_download(s, api, products)

    '''
    ## Create Image
    '''
    if redo:
        image_paths = [create_rgb(download) for download in download_paths]
        images = [rio.open(image) for image in image_paths]
        composite = combine_images(images)
        cropped = crop_to_box(composite, bbox)
        write_image(cropped, "/tmp/cropped.tiff")
    else:
        cropped = rio.open("/tmp/cropped.tiff")

    '''
    ## First Look
    '''

    #%matplotlib notebook
    matplot_image(gca(), cropped)
    matplot_route(gca(), cropped, df)

    '''
    ## Calculate Elevation
    '''
    elevation = create_elevation(s, image)
