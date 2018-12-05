
from math import pi, cos

from .tree import LinearMixin, BaseTree, QuadraticMixin, ExponentialMixin

RADIUS = 6371000
RADIAN = pi / 180


class LocalTangent:
    '''
    Assume a spherical earth and local linear approximations to convert from (lon, lat) to (x, y) in m.
    '''

    def __init__(self):
        self.__zero = None

    def normalize(self, point):
        if self.__zero is None:
            self.__zero = point
        zx, zy = self.__zero
        lon, lat = point[0] - zx, point[1] - zx
        while lon > 180: lon -= 360
        while lon <= -180: lon += 360
        return RADIUS * RADIAN * lon * cos(self.__zero[1]), RADIUS * RADIAN * lat

    def denormalize(self, point):
        zx, zy = self.__zero
        x, y = point
        return zx + x / (RADIUS * RADIAN * cos(self.__zero[1])), zy + y / (RADIUS * RADIAN)


class SphericalMixin:

    def __init__(self, *args, **kargs):
        self.__plane = LocalTangent()
        super().__init__(*args, **kargs)

    def _normalize_point(self, point):
        return self.__plane.normalize(point)

    def _denormalize_point(self, point):
        return self.__plane.denormalize(point)


class SLRTree(LinearMixin, SphericalMixin, BaseTree): pass


class SQRTree(QuadraticMixin, SphericalMixin, BaseTree): pass


class SERTree(ExponentialMixin, SphericalMixin, BaseTree): pass
