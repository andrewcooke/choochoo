
from logging import getLogger

import numpy as np

from ..msil2a.image import xy_to_latlon
from ..sortem.bilinear import bilinear_elevation_from_constant

log = getLogger(__name__)


def create_elevation(s, image):
    x, y = np.mgrid[0:image.width, 0:image.height]
    x, y = x.reshape(image.width * image.height), y.reshape(image.width * image.height)
    lat, lon = xy_to_latlon(image, x, y)
    oracle = bilinear_elevation_from_constant(s)
    elevation = np.array([oracle.elevation(lat, lon) for lat, lon in zip(lat, lon)])
    return elevation.reshape(image.width, image.height)
