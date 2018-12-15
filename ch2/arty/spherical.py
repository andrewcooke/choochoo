
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
        return zx + x / (RADIUS * RADIAN * cos(self.__zero[1])), zy + y / (RADIUS * RADIAN)


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


# TODO - need to patch latitude too for tangent!!!

class GlobalLongitude:
    '''
    Cover longitude in overlapping local trees then query both the central tree and those to either side.

    We can either store three times and retrieve once, or store once and retrieve three times.
    '''

    def __init__(self, tree=SQRTree, n=36, favour_read=True):
        self.__tree = tree
        self.__n = n
        self.__trees = [None] * n
        self.__favour_read = favour_read

    def __delegate(self, i):
        if i >= self.__n: i -= self.__n
        if i < 0: i += self.__n
        if self.__trees[i] is None:
            tree = self.__tree()
            # set the local tangent to the centre point  TODO - check
            bin_width = 360 / self.__n
            lon = (i + 0.5) * bin_width - 180
            tree.add([(lon, 0)], None)
            tree.delete([(lon, 0)])
            self.__trees[i] = tree
        return self.__trees[i]

    def __delegates(self, points, read=True):
        lon = norm180(points[0][0])
        bin_width = 360 / self.__n
        i = int((lon + 180) // bin_width)
        yield self.__delegate(i)
        if self.__favour_read != read:
            yield self.__delegate(i-1)
            yield self.__delegate(i+1)

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
