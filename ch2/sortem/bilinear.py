
from .file import SRTM1_DIR, SAMPLES, ElevationSupport, elevation_from_constant


def bilinear_elevation_from_constant(log, s, dir_name=SRTM1_DIR):
    return elevation_from_constant(log, s, BilinearElevation, dir_name=dir_name)


class BilinearElevation(ElevationSupport):
    '''
    Provide elevation data from the files in `dir` which should be hgt files with standard naming,
    either zipped or unzipped, downloaded from http://dwtkns.com/srtm30m/.

    All coords are "GPS coords" afaict.

    If dir is None then None will be return as elevation for all queries.

    If dir is not None and a file is missing for a particular lat/lon then an exception is raised.

    Elevations are bilinear interpolated from the surrounding arcsec grid.
    '''

    def elevation(self, lat, lon):
        if self._dir:
            flat, flon, h = self._lookup(lat, lon)
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
