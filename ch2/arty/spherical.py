
from math import pi, cos

from .tree import LinearMixin, BaseTree, QuadraticMixin, ExponentialMixin, CartesianMixin

RADIUS = 6371000
RADIAN = pi / 180


def norm180(x):
    while x > 180: x -= 360
    while x <= -180: x += 360
    return x


class LocalTangent:
    '''
    Assume a spherical earth and local linear approximations to convert from (lon, lat) to (x, y) in m.
    '''

    def __init__(self, point=None):
        self.__zero = None
        if point is not None:
            self.normalize(point)

    def normalize(self, point):
        if self.__zero is None:
            self.__zero = point
        zx, zy = self.__zero
        lon, lat = norm180(point[0] - zx), point[1] - zy
        return RADIUS * RADIAN * lon * cos(self.__zero[1]), RADIUS * RADIAN * lat

    def denormalize(self, point):
        zx, zy = self.__zero
        x, y = point
        return norm180(zx + x / (RADIUS * RADIAN * cos(self.__zero[1]))), zy + y / (RADIUS * RADIAN)


class SphericalMixin(CartesianMixin):

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


class Global:
    '''
    Tile a globe.
    '''

    def __init__(self, tree=SQRTree, n=36, favour_read=True):
        self.__tree = tree
        self.__n = n
        self.__trees = [[None] * n for _ in range(n)]
        self.__favour_read = favour_read

    def __norm_n(self, i):
        while i < 0: i += self.__n
        while i >= self.__n: i -= self.__n
        return i

    def __delegate(self, i, j):
        i, j = self.__norm_n(i), self.__norm_n(j)
        if self.__trees[i][j] is None:
            tree = self.__tree()
            # set the local tangent to the centre point
            bin_width = 360 / self.__n
            lon = (i + 0.5) * bin_width - 180
            lat = (j + 0.5) * bin_width - 180
            tree.add([(lon, lat)], None)
            tree.delete([(lon, lat)])
            self.__trees[i][j] = tree
        return self.__trees[i][j]

    def __delegates(self, points, read=True):
        lon, lat = points[0]
        i, j = int(self.__n * lon / 360), int(self.__n * lat / 180)
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                yield self.__delegate(i + di, j + dj)

    def get(self, points, value=None, match=None, border=None):
        for delegate in self.__delegates(points):
            yield from delegate.get(points, value=value, match=match, border=border)

    def get_items(self, points, value=None, match=None, border=None):
        for delegate in self.__delegates(points):
            yield from delegate.get_items(points, value=value, match=match, border=border)

    def add(self, points, value, border=None):
        for delegate in self.__delegates(points, read=False):
            delegate.add(points, value, border=border)

    def add_all(self, items, border=None):
        for (points, value) in items:
            for delegate in self.__delegates(points, read=False):
                delegate.add(points, value, border=border)

    def delete(self, points, value=None, match=None, border=None):
        '''
        This purposefully does not return number deleted.  If you are relying on that value,
        your code should not be using this wrapper.
        '''
        for delegate in self.__delegates(points):
            delegate.delete(points, value=value, match=match, border=border)

    def delete_one(self, points, value=None, match=None, border=None):
        for delegate in self.__delegates(points):
            delegate.delete_one(points, value=value, match=match, border=border)

    def __getitem__(self, points):
        return self.get(points)

    def __setitem__(self, points, value):
        self.add(points, value)

    def __delitem__(self, points):
        self.delete(points)

    def __bool__(self):
        return any(bool(t) for t in self.__trees)
