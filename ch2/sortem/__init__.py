
from functools import lru_cache
from math import floor
from os.path import join, exists
from zipfile import ZipFile

import numpy as np

from ..squeal import Constant

SRTM1_DIR = 'SRTM1.Dir'
SAMPLES = 3601
# from view-source:http://dwtkns.com/srtm30m/
BASE_URL = 'http://e4ftl01.cr.usgs.gov/MEASURES/SRTMGL1.003/2000.02.11/'
EXTN = '.SRTMGL1.hgt.zip'


# lots of credit to https://github.com/aatishnn/srtm-python/blob/master/srtm.py
# (although that has bugs...)


def oracle_from_constant(log, s, dir_name=SRTM1_DIR):
    try:
        dir = Constant.get(s, dir_name).at(s).value
    except:
        log.warn('STRM1 config - define %s in constants for elevation data' % dir_name)
        dir = None
    return ElevationOracle(log, dir)


class ElevationOracle:
    '''
    Provide elevation data from the files in `dir` which should be hgt files with standard naming,
    either zipped or unzipped, downloaded from http://dwtkns.com/srtm30m/.

    All coords are "GPS coords" afaict.

    If dir is None then None will be return as elevation for all queries.

    If dir is not None and a file is missing for a particular lat/lon then an exception is raised.

    Elevations are bilinear interpolated from the surrounding arcsec grid.
    '''

    def __init__(self, log, dir):
        self._log = log
        self._dir = dir

    def elevation(self, lat, lon):
        if self._dir:
            flat, flon = floor(lat), floor(lon)
            # construct the path in the reader so it's skipped if we hit the cache
            h = cached_file_reader(self._log, self._dir, flat, flon)
            x = (lon - flon) * (SAMPLES - 1)
            y = (lat - flat) * (SAMPLES - 1)  # -1 because weird inclusive-at-each-side tiling
            i, j = int(x), int(y)
            # bilinear
            # it's ok to use +1 blindly here because we're never on the top/right cells or we'd be in
            # a different tile.
            k = y - j
            h0 = h[j, i] * (1-k) + h[j+1, i] * k
            h1 = h[j, i+1] * (1-k) + h[j+1, i+1] * k
            k = x - i
            return h0 * (1-k) + h1 * k
        else:
            return None


@lru_cache(4)  # 4 means our tests are quick...
def cached_file_reader(log, dir, flat, flon):
    if not exists(dir):
        raise Exception('SRTM1 directory %s missing' % dir)
    # https://wiki.openstreetmap.org/wiki/SRTM
    # The official 3-arc-second and 1-arc-second data for versions 2.1 and 3.0 are divided into 1°×1° data tiles.
    # The tiles are distributed as zip files containing HGT files labeled with the coordinate of the southwest cell.
    # For example, the file N20E100.hgt contains data from 20°N to 21°N and from 100°E to 101°E inclusive.
    root = '%s%02d%s%03d' % ('S' if flat < 0 else 'N', abs(flat), 'W' if flon < 0 else 'E', abs(flon))
    hgt_file = root + '.hgt'
    hgt_path = join(dir, hgt_file)
    zip_path = join(dir, root + EXTN)
    if exists(hgt_path):
        log.debug('Reading %s' % hgt_path)
        with open(hgt_path, 'rb') as input:
            data = input.read()
    elif exists(zip_path):
        log.debug('Reading %s' % zip_path)
        with open(zip_path, 'rb') as input:
            zip = ZipFile(input)
            log.debug('Found %s' % zip.filelist)
            data = zip.open(hgt_file).read()
    else:
        # i tried automating download, but couldn't get ouath2 to work
        log.warn('Download %s' % BASE_URL + root + EXTN)
        raise Exception('Missing %s' % hgt_file)
    return np.flip(np.frombuffer(data, np.dtype('>i2'), SAMPLES * SAMPLES).reshape((SAMPLES, SAMPLES)), 0)
