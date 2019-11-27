
import datetime as dt
from itertools import groupby

from sentinelsat import SentinelAPI
from shapely.geometry import MultiPoint
from shapely.wkt import loads

from ch2.data import *
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

    activity = activity_statistics(s, LATITUDE, LONGITUDE,
                                   local_time=local_time, activity_group_name=activity_group_name)
    activity = activity.dropna()
    points = MultiPoint(activity.apply(lambda row: (row[LONGITUDE], row[LATITUDE]), axis='columns'))
    footprint = points.convex_hull

    api = SentinelAPI(user, passwd, 'https://scihub.copernicus.eu/dhus')
    products = api.query(area=footprint, platformname='Sentinel-2', date=('NOW-1YEAR', 'NOW'),
                         processinglevel='Level-2A', cloudcoverpercentage=(0, 10))
    products = sorted(products.values(), key=lambda product: product['beginposition'], reverse=True)
    footprint_areas = sorted((loads(product['footprint']).area for product in products), reverse=True)
    footprint_cutoff = footprint_areas[0] * 0.9
    products = [product for product in products if loads(product['footprint']).area > footprint_cutoff]
    neighbours = [a['beginposition'] - b['beginposition'] < dt.timedelta(hours=3)
                  for a, b in zip(products, products[1:])]

    def make_counter():
        count = 0

        def counter(neighbour):
            nonlocal count
            if not neighbour: count += 1
            return count

        return counter

    counter = make_counter()
    groups = [0] + [counter(neighbour) for neighbour in neighbours]

    productss = [[pg[0] for pg in pgs] for g, pgs in groupby(zip(products, groups), key=lambda pg: pg[1])]
    max_size = max(*[len(products) for products in productss])
    productss = [products for products in productss if len(products) == max_size]
    products = productss[0]
    print([product['summary'] for product in products])
