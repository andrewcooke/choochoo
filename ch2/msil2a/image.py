
from collections import defaultdict
from glob import glob
from logging import getLogger
from os.path import join, exists

import numpy as np
import rasterio as rio
from pyproj import Proj, transform
from rasterio.enums import Resampling, ColorInterp
from rasterio.features import shapes
from rasterio.mask import mask
from rasterio.merge import merge
from rasterio.plot import reshape_as_image
from rasterio.warp import calculate_default_transform, reproject, transform_geom
from shapely.geometry import Polygon, mapping, box

from ch2.stoats.names import LATITUDE, LONGITUDE
from ..lib import drop_trailing_slash, median

log = getLogger(__name__)


def read_band(path, band):
    files = glob(join(path, '*.SAFE', 'GRANULE', '*', 'IMG_DATA', 'R10m', f'*_{band}_10m.jp2'))
    if len(files) != 1:
        raise Exception(f'Unexpected structure under {path} for band {band}')
    band = rio.open(files[0])
    log.debug(f'Opened {files[0]}')
    log.debug(band.profile)
    return band


def read_rgb(path):
    b = read_band(path, 'B02')
    g = read_band(path, 'B03')
    r = read_band(path, 'B04')
    return r, g, b


def create_rgb(path):
    '''
    The path points to a directory; we create an RGB composite from the data in the directory and save to the
    same path with '.tiff' appended.
    See https://towardsdatascience.com/satellite-imagery-access-and-analysis-in-python-jupyter-notebooks-387971ece84b
    '''
    tiff = drop_trailing_slash(path) + '.tiff'
    if exists(tiff):
        log.warning(f'{tiff} already exists')
    else:
        log.debug('Reading layers')
        r, g, b = read_rgb(path)
        profile = r.profile
        profile.update({'driver': 'GTiff',
                        'count': 3,
                        'dtypes': (r.dtypes[0], g.dtypes[0], b.dtypes[0]),
                        'photometric': 'RGB'})
        with rio.open(tiff, 'w', **profile) as out:
            log.debug('Writing red layer')
            out.write(r.read(1), 1)
            log.debug('Writing green layer')
            out.write(g.read(1), 2)
            log.debug('Writing blue layer')
            out.write(b.read(1), 3)
            out.close()
        log.debug(f'Wrote {path}')
    return tiff


def first(images):
    return images[0]


def split(images, choose=first):
    reference = choose(images)
    return reference, [image for image in images if image is not reference]


def force_same_crs(images, choose=first):
    reference, rest = split(images, choose)
    same = [reference]
    while rest:
        image = rest.pop()
        if image.crs != reference.crs:
            log.info(f'Converting {image.crs} to {reference.crs}')
            image = reproject_to_memory(image, reference.crs)
        same.append(image)
    return same


def reproject_to_memory(image, crs):
    # https://rasterio.readthedocs.io/en/stable/topics/reproject.html
    transform, width, height = calculate_default_transform(image.crs, crs, image.width, image.height, *image.bounds)
    profile = image.profile.copy()
    profile.update({'crs': crs,
                    'transform': transform,
                    'width': width,
                    'height': height})
    transformed = rio.MemoryFile().open(**profile)
    for i in range(1, image.count + 1):
        reproject(source=rio.band(image, i),
                  destination=rio.band(transformed, i),
                  src_transform=image.transform,
                  src_crs=image.crs,
                  dst_transform=transform,
                  dst_crs=crs,
                  resampling=Resampling.nearest)
    return transformed


def shape_to_polygon(shape):  # to do - shapely shape() should do this?
    geometry, value = shape
    if geometry['type'] != 'Polygon':
        raise Exception(f'Unexpected geometry: {shape}')
    return Polygon(*geometry['coordinates'])


def most_intersecting(footprints, targets, candidates, choose=first):
    score_to_images = defaultdict(list)
    for candidate in candidates:
        score = sum(1 if footprints[target].intersection(footprints[candidate]) else 0 for target in targets)
        score_to_images[score].append(candidate)
    scores = sorted(score_to_images.keys(), reverse=True)
    if scores[0] == 0:
        raise Exception('Disjoint images')
    return choose(score_to_images[scores[0]])


def create_image(template, data, transform):
    log.debug('Creating new image')
    profile = template.profile.copy()
    profile.update({'driver': 'GTiff',
                    'height': data.shape[1],
                    'width': data.shape[2],
                    'transform': transform,
                    'photometric': 'RGB'})
    new_image = rio.MemoryFile().open(**profile)
    new_image.write(data)
    return new_image


def crop_to_shape(image, shape):
    cropped, transform = mask(image, [shape], crop=True)
    return create_image(image, cropped, transform)


def measure_scaling(footprints, targets, candidate):
    scalings = []
    for target in targets:
        overlap = footprints[target].intersection(footprints[candidate])
        if overlap:
            log.debug(f'{target} and {candidate} overlap at {overlap}')
            crop_target = crop_to_shape(target, overlap)
            crop_candidate = crop_to_shape(candidate, overlap)
            scalings.append(sorted(crop_target.read(i).mean() / crop_candidate.read(i).mean() for i in range(1, 4))[1])
    if not scalings:
        raise Exception('Disjoint images')
    return median(scalings)


def force_same_scaling(images, choose=first):
    footprints = {image: shape_to_polygon(next(shapes(image.dataset_mask(), transform=image.transform)))
                  for image in images}
    reference, rest = split(images, choose)
    scaled = [reference]
    while rest:
        candidate = most_intersecting(footprints, scaled, rest)
        rest.remove(candidate)
        scale = measure_scaling(footprints, scaled, candidate)
        log.info(f'Scaling {candidate} by {scale}')
        profile = candidate.profile
        profile.update({'photometric': 'RGB'})
        copy = rio.MemoryFile().open(**profile)
        types = {i: dtype for i, dtype in zip(candidate.indexes, candidate.dtypes)}
        for i in range(1, 4):
            copy.write((candidate.read(i) * scale).astype(types[i]), i)
        scaled.append(copy)
    return scaled


def combine_images(images, choose=first):
    log.debug(f'Combining {images}')
    images = force_same_crs(images, choose=choose)
    images = force_same_scaling(images, choose=choose)
    return create_image(images[0], *merge(images))


def crop_to_box(image, gps_bbox):
    '''
    This differs from crop to shape in that:
    1 - the bbox coords are WGS84 lat lon (GPS)
    2 - we want the result to be a 'square' image (not a diamond)
    '''
    # for some reason the gps_bbox cannot be a shapely object; it has to be a geojson dict
    crs_bbox = transform_geom('WGS84', image.crs, mapping(gps_bbox))
    pixel_bbox = [image.index(*xy) for xy in crs_bbox['coordinates'][0]]
    xs, ys = zip(*pixel_bbox)
    # maybe we should do something smarter here to ensure we always have data?
    # like take the miniumum of the maximal values, etc.
    pixel_bbox = box(min(xs), min(ys), max(xs), max(ys))
    crs_bbox = Polygon([image.xy(*xy) for xy in pixel_bbox.exterior.coords])
    return crop_to_shape(image, crs_bbox)


def write_image(image, path):
    with rio.open(path, 'w', **image.profile) as dest:
        dest.write(image.read())


def plot_image(ax, image):
    # based on rasterio.plot, but accepts in-memory images
    color_map = dict(zip(image.colorinterp, image.indexes))
    rgb_indexes = [color_map[ci] for ci in
                   (ColorInterp.red, ColorInterp.green, ColorInterp.blue)]
    arr = image.read(rgb_indexes, masked=True)
    arr = reshape_as_image(arr)
    # https://stackoverflow.com/questions/24739769/matplotlib-imshow-plots-different-if-using-colormap-or-rgb-array
    lo, hi = np.min(arr), np.max(arr)
    arr = ((arr - lo) / (hi - lo)) ** (1 / 2.2)
    ax.imshow(arr)


def plot_route(ax, image, df):
    # https://gis.stackexchange.com/a/129857
    lonlat = [(row[LONGITUDE], row[LATITUDE]) for time, row in df.iterrows()]
    p1 = Proj(proj='latlong', datum='WGS84')
    p2 = Proj(image.crs)
    eastnorth = zip(*transform(p1, p2, *zip(*lonlat)))
    rowcol = [image.index(e, n) for e, n in eastnorth]
    xy = [(col, row) for row, col in rowcol]
    ax.plot(*zip(*xy), color='red', linewidth='1')
