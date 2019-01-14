
from functools import lru_cache
from math import floor
from os.path import join

import numpy as np

from ..squeal import Constant


SRTM1_DIR = 'SRTM1.Dir'
SAMPLES = 3601


# lots of credit to https://github.com/aatishnn/srtm-python/blob/master/srtm.py
# (although that has bugs...)


def oracle_from_constant(log, s, name=SRTM1_DIR):
    try:
        dir = Constant.get(s, name).at(s).value
    except:
        log.warn('No STRM1 data - define %s in constants for elevation data' % SRTM1_DIR)
        dir = None
    return ElevationOracle(log, dir)


class ElevationOracle:

    def __init__(self, log, dir):
        self._log = log
        self._dir = dir  # if None, will simply return None

    def elevation(self, lat, lon):
        if self._dir:
            h = cached_file_reader(join(self._dir, self.file_name(lat, lon)))
            x = (lon - floor(lon)) * (SAMPLES - 1)
            y = (lat - floor(lat)) * (SAMPLES - 1)  # -1 because weird inclusive-at-each-side tiling
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

    # https://wiki.openstreetmap.org/wiki/SRTM
    # The official 3-arc-second and 1-arc-second data for versions 2.1 and 3.0 are divided into 1°×1° data tiles.
    # The tiles are distributed as zip files containing HGT files labeled with the coordinate of the southwest cell.
    # For example, the file N20E100.hgt contains data from 20°N to 21°N and from 100°E to 101°E inclusive.
    def file_name(self, lat, lon):
        return '%s%02d%s%03d.hgt' % \
               ('S' if lat < 0 else 'N', abs(floor(lat)), 'W' if lon < 0 else 'E', abs(floor(lon)))


@lru_cache(4)  # 4 means our tests are quick...
def cached_file_reader(path):
    with open(path, 'rb') as data:
        return np.flip(np.fromfile(data, np.dtype('>i2'), SAMPLES * SAMPLES).reshape((SAMPLES, SAMPLES)), 0)
