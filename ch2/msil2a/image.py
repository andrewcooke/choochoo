
from glob import glob
from logging import getLogger
from os.path import join, exists

import rasterio as rio

from ..lib import drop_trailing_slash

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

