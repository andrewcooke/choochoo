
from functools import lru_cache

import numpy as np
from scipy.interpolate import RectBivariateSpline

from .file import SRTM1_DIR, SAMPLES, ElevationSupport, elevation_from_constant, cached_file_reader


def spline_elevation_from_constant(log, s, dir_name=SRTM1_DIR, smooth=0):
    return elevation_from_constant(log, s, lambda log, dir: SplineElevation(log, dir, smooth), dir_name=dir_name)


class SplineElevation(ElevationSupport):

    def __init__(self, log, dir, smooth=0):
        super().__init__(log, dir, make_cached_spline_builder(smooth))

    def elevation(self, lat, lon):
        if self._dir:
            _, _, spline = self._lookup(lat, lon)
            return spline([lat], [lon])[0][0]  # it's a grid for all x and y, hence 2d
        else:
            return None


def make_cached_spline_builder(smooth):

    @lru_cache(4)  # 4 means our tests are quick (and should tile a local patch)
    def cached_spline_builder(log, dir, flat, flon):
        h = cached_file_reader(log, dir, flat, flon)
        x, y = np.linspace(flat, flat+1, SAMPLES), np.linspace(flon, flon+1, SAMPLES)
        # not 100% sure on the scaling of s but it seems to be related to sum of errors at all points
        # however, a scaling of SAMPLES * SAMPLES means that smooth=1 gives a numerical error, so add 10
        return RectBivariateSpline(x, y, h, s=smooth * SAMPLES * SAMPLES * 10)

    return cached_spline_builder
