
from logging import getLogger

import numpy as np

from ch2.lib.image import xy_to_latlon, extract_rgb, create_image
from ..sortem.bilinear import bilinear_elevation_from_constant

log = getLogger(__name__)


def create_elevation(s, image):
    x, y = np.mgrid[0:image.height, 0:image.width]
    x, y = x.reshape(image.width * image.height), y.reshape(image.width * image.height)
    lat, lon = xy_to_latlon(image, x, y)
    oracle = bilinear_elevation_from_constant(s)
    elevation = np.array([oracle.elevation(lat, lon) for lat, lon in zip(lat, lon)])
    return elevation.reshape(image.height, image.width)


# def plot_elevation(elevation):
#     # import pdb; pdb.set_trace()
#     mlab.init_notebook('x3d')
#     mlab.options.offscreen = False
#     mlab.figure(size=(640, 800), bgcolor=(0.16, 0.28, 0.46))
#     mlab.surf(elevation, warp_scale=0.2)
#     mlab.show()
    # mlab.test_plot3d()


def add_elevation(image, elevation):
    r, g, b = extract_rgb(image)
    e = ((elevation / np.max(elevation)) * np.iinfo(r.dtype).max).astype(r.dtype)
    return create_image(image, np.stack([r, g, b, e]))
