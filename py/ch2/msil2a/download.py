
import datetime as dt
from collections import defaultdict
from itertools import groupby
from logging import getLogger
from os.path import exists, join
from zipfile import ZipFile

from shapely.wkt import loads

from ..sql import Constant

log = getLogger(__name__)


MSIL2A_DIR_CNAME = 'msil2a_dir'


def clean_and_group_products(products):
    products = sorted(products.values(), key=lambda product: product['beginposition'], reverse=True)
    footprint_areas = sorted((loads(product['footprint']).area for product in products), reverse=True)
    footprint_cutoff = footprint_areas[0] * 0.9
    products = [product for product in products if loads(product['footprint']).area > footprint_cutoff]
    log.debug(f'After footprint area cutoff of {footprint_cutoff} have {len(products)} products')
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
    log.debug(f'Grouped products into {len(productss)} groups, with maximum size {max_size}')
    productss = [products for products in productss if len(products) == max_size]
    log.debug(f'Finally have {len(productss)} maximally-sized groups')
    return productss


def score_productss(productss, dir):
    scored = defaultdict(list)
    for products in productss:
        score, hit, miss = 0, [], []
        for product in products:
            if exists(join(dir, product['uuid'])):
                hit.append(product)
            else:
                score += 1
                miss.append(product)
        scored[score].append((hit, miss))
    scores = sorted(list(scored.keys()))
    log.debug(f'Scores range from {scores[0]} to {scores[-1]}')
    return scored[scores[0]][0]


def check_and_unpack_success(products, success, data_dir):
    products_by_id = {product['uuid']: product for product in products}
    for id in success:
        if id not in products_by_id:
            raise Exception(f'Downloaded unexpected {id}')
        if not success[id]['path']:
            log.debug(success)
            raise Exception(f'No path for {id}')
        src = success[id]['path']
        dest = join(data_dir, id)
        if exists(dest):
            raise Exception(f'Destination {dest} already exists')
        log.debug(f'Extracting {id} to {dest}')
        ZipFile(src).extractall(path=dest)


def download_missing(api, products, data_dir, download_dir='/tmp'):
    '''
    Download to download_dir and unpack in data_dir.
    We do not delete from download_dir - the system will do that for us and the underlying lib will use it as a cache
    if for some reason the unpacked data were deleted.
    '''
    # list comprehension to work round bug in sentinelsat 0.13
    success, lta, failure = api.download_all([product['uuid'] for product in products], directory_path=download_dir)
    log.debug(f'success: {len(success)}; lta: {len(lta)}; failure: {len(failure)}')
    if success:
        check_and_unpack_success(products, success, data_dir)
    if failure:
        raise Exception(f'Failed to download {", ".join(failure)}.')
    if lta:
        raise Exception(f'Some downloads triggered LTA ({", ".join(lta.keys())})')


def cached_download(s, api, products, dir_name=MSIL2A_DIR_CNAME):
    '''
    The products (a dict) are the result if a query to SentinelAPI.  They describe various candidate files.
    We assume that products at nearby times need to be combined so must be downloaded together.
    This routine tried to find a suitable set of products that have full coverage, can be downloaded
    together, and preferably already exist on disk.
    '''
    productss = clean_and_group_products(products)
    msil2a_dir = Constant.get(s, dir_name).at(s).value
    hit, miss = score_productss(productss, msil2a_dir)
    if miss:
        download_missing(api, miss, msil2a_dir)
    return [join(msil2a_dir, product['uuid']) for product in hit+miss]
