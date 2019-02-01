
from functools import lru_cache
from genericpath import exists
from math import floor
from os.path import join
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


@lru_cache(4)  # 4 means our tests are quick (and should tile a local patch)
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
        log.warning('Download %s' % BASE_URL + root + EXTN)
        raise Exception('Missing %s' % hgt_file)
    return np.flip(np.frombuffer(data, np.dtype('>i2'), SAMPLES * SAMPLES).reshape((SAMPLES, SAMPLES)), 0)


class ElevationSupport:

    def __init__(self, log, dir, reader=cached_file_reader):
        self._log = log
        self._dir = dir
        self._reader = reader

    def _lookup(self, lat, lon):
        flat, flon = floor(lat), floor(lon)
        # construct the path in the reader so it's skipped if we hit the cache
        return flat, flon, self._reader(self._log, self._dir, flat, flon)


def elevation_from_constant(log, s, interp, dir_name=SRTM1_DIR):
    try:
        dir = Constant.get(s, dir_name).at(s).value
    except:
        log.warning('STRM1 config - define %s in constants for elevation data' % dir_name)
        dir = None
    return interp(log, dir)
