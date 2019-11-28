
from ch2.data import *
from ch2.msil2a import query_activity, cached_download, create_rgb
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

    s = session('-v2 -f ~/.ch2/database-0-27.sql')

    api, products = query_activity(s, user, passwd, local_time, activity_group_name)
    downloads = cached_download(s, api, products)
    print(downloads)

    '''
    ## Create Composite Image
    '''
    images = [create_rgb(download) for download in downloads]
    print(images)
