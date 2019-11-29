
from collections import defaultdict
from glob import glob
from logging import getLogger
from os.path import join, exists

import rasterio as rio
from rasterio.enums import Resampling
from rasterio.features import shapes
from rasterio.mask import mask
from rasterio.warp import calculate_default_transform, reproject
from shapely.geometry import Polygon

from ..lib import drop_trailing_slash, median

log = getLogger(__name__)


def open_band(path, band):
    files = glob(join(path, '*.SAFE', 'GRANULE', '*', 'IMG_DATA', 'R10m', f'*_{band}_10m.jp2'))
    if len(files) != 1:
        raise Exception(f'Unexpected structure under {path} for band {band}')
    band = rio.open(files[0])
    log.debug(f'Opened {files[0]}')
    log.debug(band.profile)
    return band


def open_rgb(path):
    b = open_band(path, 'B02')
    g = open_band(path, 'B03')
    r = open_band(path, 'B04')
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
        r, g, b = open_rgb(path)
        with rio.open(tiff, 'w', driver='Gtiff', width=r.width, height=r.height, count=3,
                      crs=r.crs, transform=r.transform, dtype=r.dtypes[0], photometric='RGB') as out:
            out.write(r.read(1), 1)
            out.write(g.read(1), 2)
            out.write(b.read(1), 3)
            profile = out.profile
            out.close()
        log.debug(f'Wrote {path}')
        log.debug(profile)
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
    kwargs = image.meta.copy()
    kwargs.update({
        'crs': crs,
        'transform': transform,
        'width': width,
        'height': height
    })
    transformed = rio.MemoryFile().open(**kwargs)
    for i in range(1, image.count + 1):
        reproject(source=rio.band(image, i),
                  destination=rio.band(transformed, i),
                  src_transform=image.transform,
                  src_crs=image.crs,
                  dst_transform=transform,
                  dst_crs=crs,
                  resampling=Resampling.nearest)
    return transformed


def shape_to_polygon(shape):
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


def crop_to_shape(image, shape):
    cropped, transform = mask(image, [shape], crop=True)
    meta = image.meta.copy()
    meta.update({"driver": "GTiff",
                 "height": cropped.shape[1],
                 "width": cropped.shape[2],
                 "transform": transform})
    transformed = rio.MemoryFile().open(**meta)
    transformed.write(cropped)
    return transformed


def measure_scaling(footprints, targets, candidate):
    scalings = []
    for target in targets:
        overlap = footprints[target].intersection(footprints[candidate])
        if overlap:
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
        copy = rio.MemoryFile().open(**candidate.meta)
        types = {i: dtype for i, dtype in zip(candidate.indexes, candidate.dtypes)}
        for i in range(1, 4):
            copy.write((candidate.read(i) * scale).astype(types[i]), i)
        scaled.append(copy)
    return scaled
