
from logging import getLogger

import rasterio as rio
import numpy as np
from pyproj import Proj, transform
from rasterio.enums import ColorInterp
from rasterio.plot import reshape_as_image
from scipy.ndimage import shift
from skimage.draw import polygon_perimeter

from ch2.stats.names import LATITUDE, LONGITUDE

log = getLogger(__name__)

RGB = 'RGB'
RGB_INDICES = (ColorInterp.red, ColorInterp.green, ColorInterp.blue)
GTIFF = 'GTiff'

COUNT = 'count'
CRS = 'crs'
DRIVER = 'driver'
DTYPES = 'dtypes'
HEIGHT = 'height'
PHOTOMETRIC = 'photometric'
TRANSFORM = 'transform'
WIDTH = 'width'

LATLONG = 'latlong'
WGS84 = 'WGS84'


def create_image(template, data, transform=None):
    log.debug('Creating new image')
    transform = transform or template.transform
    profile = template.profile.copy()
    profile.update({DRIVER: GTIFF,
                    COUNT: data.shape[0],
                    HEIGHT: data.shape[1],
                    WIDTH: data.shape[2],
                    TRANSFORM: transform,
                    PHOTOMETRIC: RGB})
    new_image = rio.MemoryFile().open(**profile)
    new_image.write(data)
    return new_image


def write_image(image, path):
    with rio.open(path, 'w', **image.profile) as dest:
        dest.write(image.read())


def read_image_rgb(path):
    image = rio.open(path, 'r+')
    image.colorinterp = RGB
    return image


def extract_rgb(image):
    color_map = dict(zip(image.colorinterp, image.indexes))
    rgb_indices = [color_map[ci] for ci in RGB_INDICES]
    return image.read(rgb_indices, masked=True)


def matplot_image(ax, image):
    # based on rasterio.plot, but accepts in-memory images
    rgb = extract_rgb(image)
    rgb = reshape_as_image(rgb)
    # https://stackoverflow.com/questions/24739769/matplotlib-imshow-plots-different-if-using-colormap-or-rgb-array
    lo, hi = np.min(rgb), np.max(rgb)
    rgb = ((rgb - lo) / (hi - lo)) ** (1 / 2.2)
    ax.imshow(rgb)


def matplot_route(ax, image, df):
    lat, lon = df[LATITUDE].values, df[LONGITUDE].values
    x, y = latlon_to_xy(image, lat, lon)
    ax.plot(x, y, color='red', linewidth='1')


def latlon_to_xy(image, lat, lon):
    # https://gis.stackexchange.com/a/129857
    p1 = Proj(proj=LATLONG, datum=WGS84)
    p2 = Proj(image.crs)
    east, north = transform(p1, p2, lon, lat)
    row, col = image.index(east, north)
    return col, row


def xy_to_latlon(image, x, y):
    east, north = image.xy(x, y)
    p1 = Proj(image.crs)
    p2 = Proj(proj=LATLONG, datum=WGS84)
    lon, lat = transform(p1, p2, east, north)
    return lat, lon


def anti_alias(input):
    output = input.copy()
    for dx in (-0.5, 0.5):
        for dy in (-0.5, 0.5):
            mask = shift(input, (dx, dy), np.float)
            output = np.maximum(output, mask)
    return output


def overlay(image, mask, rgb):
    inverse = 1 - mask
    data = extract_rgb(image)
    data = [(np.clip(layer * inverse + mask * color * np.max(layer), 0, np.max(layer))).astype(layer.dtype)
            for layer, color in zip(data, rgb)]
    return create_image(image, np.stack(data))


def overlay_route(image, lat, lon, rgb):
    x, y = latlon_to_xy(image, lat, lon)
    mask = np.zeros((image.height, image.width), dtype=np.float)
    rows, columns = polygon_perimeter(y, x, shape=mask.shape, clip=False)
    mask[rows, columns] = 1
    mask = anti_alias(mask)
    return overlay(image, mask, rgb)


