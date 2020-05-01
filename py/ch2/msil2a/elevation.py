
from logging import getLogger

import numpy as np

from ..lib.image import xy_to_latlon, extract_rgb, create_image
from ..srtm.bilinear import bilinear_elevation_from_constant

log = getLogger(__name__)


def create_elevation(s, image):
    x, y = np.mgrid[0:image.height, 0:image.width]
    x, y = x.reshape(image.width * image.height), y.reshape(image.width * image.height)
    lat, lon = xy_to_latlon(image, x, y)
    oracle = bilinear_elevation_from_constant(s)
    elevation = np.array([oracle.elevation(lat, lon) for lat, lon in zip(lat, lon)])
    return elevation.reshape(image.height, image.width)


def add_elevation(image, elevation):
    r, g, b = extract_rgb(image)
    e = ((elevation / np.max(elevation)) * np.iinfo(r.dtype).max).astype(r.dtype)
    return create_image(image, np.stack([r, g, b, e]))
