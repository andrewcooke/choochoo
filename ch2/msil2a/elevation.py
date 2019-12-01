
from logging import getLogger

import numpy as np
from mayavi import mlab

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


def plot_elevation(elevation):
    # import pdb; pdb.set_trace()
    mlab.init_notebook('x3d')
    mlab.options.offscreen = False
    mlab.figure(size=(640, 800), bgcolor=(0.16, 0.28, 0.46))
    mlab.surf(elevation, warp_scale=0.2)
    mlab.show()
    # mlab.test_plot3d()