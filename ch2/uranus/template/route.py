
import rasterio as rio

from ch2.data import *
from ch2.msil2a import *
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

    s = session('-v2')

    api, products, bbox = query_activity(s, user, passwd, local_time, activity_group_name)
    download_paths = cached_download(s, api, products)

    '''
    ## Create Composite Image
    '''
    image_paths = [create_rgb(download) for download in download_paths]
    images = [rio.open(image) for image in image_paths]
    composite = combine_images(images)

    '''
    ### Crop and Write Image
    '''

    cropped = crop_to_box(composite, bbox)
    write_image(cropped, "/tmp/foo.tiff")
