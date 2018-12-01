
from abc import ABC, abstractmethod
from enum import IntEnum


class MatchType(IntEnum):
    '''
    Control how MBRs are matched.
    '''

    EQUAL = 0  # request exactly equal to node
    CONTAINED = 1  # request contained in node
    CONTAINS = 2  # request contains node
    INTERSECTS = 3  # request and node intersect


class BaseTree(ABC):

    # nodes in the tree are (height, data) where
    #   height = 0 for leaf nodes
    #   data is [(mbr, value), (mbr, value), ...] for leaf nodes
    #   data is [(mbr, children), (mbr, children), ...] for internal nodes
    #     where children is [(height, data), (height, data), ...]
    # the empty root is (0, [])

    # insertion/retrieval semantics are subtly different to a hash table:
    #   you can ask for matches that are exactly equal, overlap, contain or are contained by the box
    #   you can store multiple values at the same key
    #   you can store the same value multiple times at the same key
    #   both the above mean that querying is an iterator over matches
    # these issues above affect deletion:
    #   you will delete everything you would match
    #   you can specify a value on deletion, which provides an additional constraint
    #   but you could still delete multiple nodes
    #   (even with equality matching, (key, value) isn't guaranteed unique)
    # in other words, if you want unique (key, value) or unique key you must enforce it yourself.

    def __init__(self, max_entries=4, min_entries=None):
        '''
        Create an empty tree.

        `max_entries` is the maximum number of children a node can have.
        This data structure was originally designed for mass storage, where such a parameter is important.
        For in-memory use, it doesn't matter so much except that larger values hit problems with quadratic
        and exponential splitting.
        Some quick tests suggest 4-8 is a reasonable choice.  You really don't want to go higher with exponential...
        '''
        if not min_entries:
            min_entries = max_entries // 2
        if min_entries > max_entries // 2:
            raise Exception('Min number of entries in a node is too high')
        if min_entries < 1:
            raise Exception('Min number of entries in a node is too low')
        self._max = max_entries
        self._min = min_entries
        self._root = (0, [])
        self.__size = 0
        self.__hash = 966038070

    def get(self, points, value=None, match=MatchType.EQUAL):
        '''
        An iterator over values of nodes that match the MBR for the given points.
        The `match` describes the kind of matching done.

        If `value` is given then only nodes with that value are found *and*
        the MBR (rather than node value) is returned.
        '''
        for contents, mbr in self.__get_node(self._root, self._normalize_mbr(points), value, match):
            if value is None:
                yield contents
            else:
                yield self._mbr_to_points(mbr)

    def __get_node(self, node, mbr, value, match):
        '''
        Internal get from node.
        '''
        height, data = node
        for mbr_node, contents_node in data:
            if height:
                if self.__descend(mbr, mbr_node, match):
                    yield from self.__get_node(contents_node, mbr, value, match)
            elif self._match(mbr, mbr_node, value, contents_node, match):
                yield contents_node, mbr_node

    def __descend(self, mbr, mbr_node, match):
        '''
        Descend in search?
        '''
        return (match in (MatchType.EQUAL, MatchType.CONTAINED) and self._contains(mbr_node, mbr)) or \
               (match in (MatchType.CONTAINS, MatchType.INTERSECTS) and self._intersects(mbr_node, mbr))

    def _match(self, mbr, mbr_node, value, value_node, match):
        '''
        Match search?
        '''
        return (value is None or value == value_node) and (
                (match == MatchType.EQUAL and mbr == mbr_node) or
                (match == MatchType.CONTAINED and self._contains(mbr_node, mbr)) or
                (match == MatchType.CONTAINS and self._contains(mbr, mbr_node)) or
                (match == MatchType.INTERSECTS and self._intersects(mbr, mbr_node)))

    def add(self, points, value):
        '''
        Add a value at the MBR of the given points.
        '''
        mbr = self._normalize_mbr(points)
        self.__add_root(0, mbr, value)
        self.__update_state(1, mbr, value)

    def __update_state(self, delta, mbr, value):
        '''
        Update size and hash.
        '''
        self.__size += delta
        # use product so that association matters (if we xored then you could rearrange values and mbrs)
        self.__hash ^= hash(mbr) * hash(value)

    def __add_root(self, target, mbr, value):
        '''
        Internal add at root.

        `target` is the height for insertion.  This allows for subtrees to be re-inserted as a whole.
        '''
        split = self.__add_node(self._root, target, value, mbr)
        if split:
            height = split[0][1][0] + 1
            self._root = (height, split)

    def __add_node(self, node, target, value, mbr):
        '''
        Internal add at node.

        `target` is the height for insertion.  This allows for subtrees to be re-inserted as a whole.
        '''
        height, data = node
        if height != target:
            i_best, mbr_best = self._best(data, mbr, height)
            child = data[i_best][1]
            # optimistically set mbr on way down; will be removed if split spills data over
            data[i_best] = (mbr_best, child)
            split = self.__add_node(child, target, value, mbr)
            if split:
                del data[i_best]
                data.extend(split)
        else:
            data.append((mbr, value))
        # at this point parent mbr still correct (set on way down)
        if len(data) > self._max:
            return self._split(height, data)

    def _best(self, data, mbr, height):
        '''
        Given a list of nodes, find the node whose area increases least when the given MBR is added.
        '''
        i_best, mbr_best, area_best, delta_area_best, len_best = None, None, None, None, None
        for i_child, (mbr_child, data) in enumerate(data):
            if i_best is None:
                i_best = i_child
                mbr_best = self._mbr_of_mbrs(mbr_child, mbr)
                area_best = self._area(mbr_best)
                delta_area_best = self._area(mbr_best) - self._area(mbr_child)
                len_best = len(data)
            else:
                mbr_merge = self._mbr_of_mbrs(mbr_child, mbr)
                area_merge = self._area(mbr_merge)
                delta_area_merge = area_merge - self._area(mbr_child)
                if delta_area_merge < delta_area_best or \
                        (delta_area_merge == delta_area_best and area_merge < area_best) or \
                        (delta_area_merge == delta_area_best and area_merge == area_best and
                         height and len(data) < len_best):
                    i_best, mbr_best, area_best, delta_area_best, len_best = \
                        i_child, mbr_merge, area_merge, delta_area_merge, len(data)
        return i_best, mbr_best

    def delete(self, points, value=None, match=MatchType.EQUAL):
        '''
        Remove entries that match the MBR of the given points and optional value.
        '''
        mbr = self._normalize_mbr(points)
        try:
            while True:
                self.__delete_one_root(mbr, value, match)
        except KeyError:
            return

    def delete_one(self, points, value=None, match=MatchType.EQUAL):
        '''
        Remove a single entry that match the MBR of the given points and optional value.

        Raises `KeyError` if no entry exists.
        '''
        self.__delete_one_root(self._normalize_mbr(points), value, match)

    def __delete_one_root(self, mbr, value, match):
        '''
        Internal deletion from root.
        '''
        found = self.__delete_one_node(self._root, mbr, value, match, 2)
        if found:
            delete, inserts, mbr_found, value_found = found
            if delete:
                self._root = (0, [])
            self.__reinsert(inserts)
            if len(self._root[1]) == 1 and self._root[0]:  # single child, not leaf
                self._root = self._root[1][0][1]  # contents of first child
            self.__update_state(-1, mbr_found, value_found)
        else:
            raise KeyError('Failed to delete %s%s' % (mbr, '' if value is None else ' (value %s)' % value))

    def __delete_one_node(self, node, mbr, value, match, local_min):
        '''
        Internal deletion from node.
        '''
        height, data = node
        for i, (mbr_node, contents_node) in enumerate(data):
            if height:
                if self.__descend(mbr, mbr_node, match):
                    found = self.__delete_one_node(contents_node, mbr, value, match, self._min)
                    if found:
                        delete, inserts, mbr_found, value_found = found
                        if delete:
                            del data[i]
                            if len(data) < local_min:
                                inserts.extend((height, *node) for node in data)
                                return True, inserts, mbr_found, value_found
                        else:
                            # something under data[i] has been deleted so recalculate mbr
                            _, (height_children, children) = data[i]
                            new_mbr = self._mbr_of_nodes(*children)
                            data[i] = (new_mbr, (height_children, children))
                        return False, inserts, mbr_found, value_found
            elif self._match(mbr, mbr_node, value, contents_node, match):
                del data[i]
                if len(data) < local_min:
                    return True, [(0, *node) for node in data], mbr_node, contents_node
                else:
                    return False, [], mbr_node, contents_node

    def __leaves(self, node, canary=True):
        '''
        Iterator over the leaves in a node.
        '''
        hash = self.__hash
        height, data = node
        for mbr, child in data:
            if canary and hash != self.__hash:
                raise RuntimeError('Tree was mutated while iterating over contents')
            if height:
                yield from self.__leaves(child)
            else:
                yield mbr, child

    def __reinsert(self, inserts):
        '''
        Reinsert sub-trees (including leaves) removed during re-arrangement on deletion.

        We try to insert whole sub-trees, but this is not always possible (if the height has changed)
        (this has a barely measurable effect on performance, but seems to be what the original paper expected).
        '''
        if self._root:
            max_height = self._root[0]
        else:
            max_height = 0
        for insert in inserts:
            if insert[0] > max_height:
                # can't add the entire tree, so re-add the leaves
                for mbr, value in self.__leaves(insert[2], False):
                    self.__add_root(0, mbr, value)
            else:
                self.__add_root(*insert)

   # standard container API

    def __len__(self):
        '''
        Expose number of entries though usual Python API.
        '''
        return self.__size

    def keys(self):
        '''
        All MBRs.
        '''
        for mbr, _ in self.__leaves(self._root):
            yield self._mbr_to_points(mbr)

    def values(self):
        '''
        All values.
        '''
        for _, value in self.__leaves(self._root):
            yield value

    def items(self):
        '''
        All (MBR, value) pairs.
        '''
        for mbr, value in self.__leaves(self._root):
            yield self._mbr_to_points(mbr), value

    def __contains__(self, points):
        '''
        Equivalent to calling get() with the standard arguments and testing for result.
        '''
        try:
            next(self.get(points))
            return True
        except StopIteration:
            return False

    def __hash__(self):
        '''
        Hash based only on contents.
        '''
        return self.__hash

    def __eq__(self, other):
        '''
        Equality based only on contents.
        '''
        if other is self:
            return True
        # important to use hash(self) and not self.__hash because hash() truncates bits
        if not isinstance(other, BaseTree) or self.__size != len(other) or hash(self) != hash(other):
            return False
        # todo - is it better to have something slower but memory efficient?
        return sorted(list(self.items())) == sorted(list(other.items()))

    def __iter__(self):
        '''
        Iterable over keys.
        '''
        return self.keys()

    def __getitem__(self, points):
        '''
        Call get() with equality and no value..
        '''
        return self.get(points)

    def __setitem__(self, points, value):
        '''
        Add a value at the MBR associated with the given points.
        '''
        self.add(points, value)

    def __delitem__(self, points):
        '''
        Delete all entries that match the MBR associated with the given points.
        '''
        self.delete(points)

    # utilities for debugging

    def dump(self):
        '''
        An iterator over the tree structure.
        '''
        height, data = self._root
        yield height + 1, self._mbr_of_nodes(*data), None  # implied mbr on all nodes
        yield from self._dump_node(self._root)

    def _dump_node(self, node):
        '''
        Internal iterator over the tree structure.
        '''
        height, data = node
        for mbr, value in data:
            yield height, mbr, None if height else value
            if height:
                yield from self._dump_node(value)

    def print(self):
        '''
        Dump the tree structure to stdout for debugging.
        '''
        for height, mbr, value in self.dump():
            print('%2d %s %s %s' %
                  (height, ' ' * (10 - height), mbr, '' if value is None else value))

    def assert_consistent(self):
        '''
        Make some basic tests of consistency.
        '''
        if self.__size and not self._root:
            raise Exception('Emtpy root (and size %d)' % self.__size)
        size = self._assert_consistent(self._root)
        if size != self.__size:
            raise Exception('Unexpected number of leaves (%d != %d)' % (size, self.__size))

    def _assert_consistent(self, node):
        '''
        Internal tests of consistency.
        '''
        if node:
            height, data = node
            if len(data) < self._min and node != self._root:
                raise Exception('Too few children at height %d' % height)
            if len(data) > self._max:
                raise Exception('Too many children at height %d' % height)
            if height:
                count = 0
                for mbr, child in data:
                    (height_child, data_child) = child
                    mbr_check = self._mbr_of_nodes(*data_child)
                    if mbr_check != mbr:
                        raise Exception('Bad MBR at height %d %s / %s' % (height, mbr_check, mbr))
                    count += self._assert_consistent(child)
                return count
            else:
                return len(data)
        else:
            return 0

    # allow different coordinate systems
    # nothing above should depend on the exact representation of point or mbr

    def _normalize_mbr(self, points):
        return self._mbr_of_points(*(self._normalize_point(p) for p in points))

    @abstractmethod
    def _normalize_point(self, point):
        raise NotImplementedError()

    @abstractmethod
    def _mbr_of_points(self, *points):
        raise NotImplementedError()

    def _mbr_of_nodes(self, *nodes):
        return self._mbr_of_mbrs(*(mbr for mbr, _ in nodes))

    @abstractmethod
    def _mbr_of_mbrs(self, *mbrs):
        raise NotImplementedError()

    def _mbr_to_points(self, mbr):
        x1, y1, x2, y2 = mbr
        return self._denormalize_point((x1, y1)), self._denormalize_point((x2, y2))

    @abstractmethod
    def _denormalize_point(self, point):
        raise NotImplementedError()

    @abstractmethod
    def _intersects(self, mbr1, mbr2):
        raise NotImplementedError()

    @abstractmethod
    def _contains(self, outer, inner):
        raise NotImplementedError()

    @abstractmethod
    def _area(self, mbr):
        raise NotImplementedError()

    # allow different split algorithms

    @abstractmethod
    def _split(self, height, nodes):
        raise NotImplementedError()

    @abstractmethod
    def _pick_seeds(self, nodes):
        raise NotImplementedError()

    @abstractmethod
    def _pick_next(self, pair, nodes):
        raise NotImplementedError()


class CartesianMixin:

    def _normalize_point(self, point):
        '''
        No normalizetion by default.
        '''
        return point

    def _denormalize_point(self, point):
        '''
        No normalizetion by default.
        '''
        return point

    def _mbr_of_points(self, *points):
        '''
        Find the MBR of a set of points,
        '''
        xs, ys = zip(*points)
        return min(xs), min(ys), max(xs), max(ys)

    def _mbr_of_mbrs(self, *mbrs):
        '''
        Find the MBR of a set of MBRs.
        '''
        x1s, y1s, x2s, y2s = zip(*mbrs)
        return min(x1s), min(y1s), max(x2s), max(y2s)

    def _intersects(self, mbr1, mbr2):
        '''
        Do the two MBR's intersect?
        '''
        x1, y1, x2, y2 = mbr1
        X1, Y1, X2, Y2 = mbr2
        return x1 <= X2 and x2 >= X1 and y1 <= Y2 and y2 >= Y1

    def _contains(self, outer, inner):
        '''
        Is the `inner` MBR contained by the `outer`?
        '''
        x1, y1, x2, y2 = outer
        X1, Y1, X2, Y2 = inner
        return x1 <= X1 and x2 >= X2 and y1 <= Y1 and y2 >= Y2

    def _area(self, mbr):
        '''
        Area of the MBR
        '''
        x1, y1, x2, y2 = mbr
        return (x2 - x1) * (y2 - y1)

    def __extremes(self, data):
        '''
        Internal routine for linear seeds.

        Measure the lowest higher bound, left-most right bound, etc, from a collection of MBRs
        and records which MRB (index) is responsible for each.
        '''
        index, extreme = None, None
        for i, (mbr, _) in enumerate(data):
            if not i:
                index = [0, 0, 0, 0]
                extreme = list(mbr)
            else:
                for j in range(2):
                    if mbr[j] > extreme[j]:   # want max of lower left
                        extreme[j] = mbr[j]
                        index[j] = i
                    if mbr[j+2] < extreme[j+2]:  # and min of upper right
                        extreme[j+2] = mbr[j+2]
                        index[j+2] = i
        return index, extreme

    def _pick_seeds(self, data):
        '''
        Choose the two MBRs that are furthest apart.

        Only called from LinearSplitMixin.
        '''
        global_mbr = self._mbr_of_nodes(*self._root[1])
        norm_x, norm_y = global_mbr[2] - global_mbr[0], global_mbr[3] - global_mbr[1]
        norm = [norm_x, norm_y, norm_x, norm_y]
        index, extremes = self.__extremes(data)
        extremes = [x / n for x, n in zip(extremes, norm)]
        if extremes[2] - extremes[0] > extremes[3] - extremes[1] and index[0] != index[2]:
            return index[0], index[2]
        elif extremes[2] - extremes[0] < extremes[3] - extremes[1] and index[1] != index[3]:
            return index[1], index[3]
        else:
            return 0, 1  # degenerate case :(

    def _exact_area_sum(self, mbr0, mbr1):
        '''
        Don't count the overlapping region twice.

        Only called from ExponentialSplitMixin.
        '''
        if not mbr0:
            return self._area(mbr1)
        elif not mbr1:
            return self._area(mbr0)
        else:
            outer = self._area(mbr0) + self._area(mbr1)
            x1, y1, x2, y2 = mbr0
            X1, Y1, X2, Y2 = mbr1
            xm1 = max(x1, X1)
            xm2 = min(x2, X2)
            ym1 = max(y1, Y1)
            ym2 = min(y2, Y2)
            if xm2 > xm1 and ym2 > ym1:
                inner = (xm2 - xm1) * (ym2 - ym1)
            else:
                inner = 0
            return outer - inner


class LatLonMixin(CartesianMixin):

    def __init__(self, *args, **kargs):
        self.__zero_lon = None
        super().__init__(*args, **kargs)

    def _normalize_angle(self, x):
        '''
        Reduce angle to (-180, 180]
        '''
        while x <= -180:
            x += 360
        while x > 180:
            x -= 360
        return x

    def _normalize_point(self, point):
        '''
        Normalize to a Cartesian patch centred on first point found.
        '''
        lon, lat = point
        if self.__zero_lon is None:
            self.__zero_lon = lon
        lon = self._normalize_angle(lon - self.__zero_lon)
        return lon, lat

    def _denormalize_point(self, point):
        '''
        Invert transform above.
        '''
        lon, lat = point
        lon = self._normalize_angle(lon + self.__zero_lon)
        return lon, lat


class LinearMixin:
    '''
    Simple node selection.
    '''

    def _split(self, height, nodes):
        '''
        Divide the nodes into two,
        '''
        i, j = self._pick_seeds(nodes)
        split = [(nodes[i][0], (height, [nodes[i]])), (nodes[j][0], (height, [nodes[j]]))]
        del nodes[max(i, j)]
        del nodes[min(i, j)]
        # indexing ugliness below is rebuilding tuple with new mbr
        while nodes:
            if len(nodes) < self._min:
                for index in 0, 1:
                    split_nodes = split[index][1][1]
                    if len(split_nodes) + len(nodes) == self._min:
                        split_nodes.extend(nodes)
                        split[index] = (self._mbr_of_nodes(*split_nodes), split[index][1])
                        return split
            node, nodes = self._pick_next(split, nodes)
            index, mbr = self._best(split, node[0], height)
            split[index] = (mbr, split[index][1])
            split[index][1][1].append(node)
        return split

    # _pick_seeds is on CartesianMixin because it's not abstracted from the coord system.

    def _pick_next(self, pair, nodes):
        node = nodes.pop()
        return node, nodes


class QuadraticMixin(LinearMixin):
    '''
    This does a better job of grouping nodes (than linear) and is not measurably slower.
    '''

    def _pick_seeds(self, nodes):
        n, area_delta_best, best = len(nodes), None, None
        for i in range(n):
            mbr_i = nodes[i][0]
            for j in range(i):
                mbr_j = nodes[j][0]
                mbr_both = self._mbr_of_mbrs(mbr_i, mbr_j)
                area_delta = self._area(mbr_both) - self._area(mbr_i) - self._area(mbr_j)
                if area_delta_best is None or area_delta > area_delta_best:
                    area_delta_best, best = area_delta, (i, j)
        return best

    def _pick_next(self, pair, nodes):
        area_delta_best, best = None, None
        for i in range(len(nodes)):
            area_delta = abs((self._area(self._mbr_of_nodes(nodes[i], pair[0])) - self._area(pair[0][0])) -
                             (self._area(self._mbr_of_nodes(nodes[i], pair[1])) - self._area(pair[1][0])))
            if area_delta_best is None or area_delta > area_delta_best:
                area_delta_best, best = area_delta, i
        node = nodes[best]
        del nodes[best]
        return node, nodes


class ExponentialMixin:
    '''
    Pick nodes by making a complete comparison of all possibilities.
    '''

    def _pick_next(self, pair, nodes):
        # avoid ABC error
        raise NotImplementedError()

    def _pick_seeds(self, nodes):
        # avoid ABC error
        raise NotImplementedError()

    # _exact_area_sum() is on CartesianMixin because it is not abstracted from the coordinate system.

    def __split_recursive(self, mbr0, mbr1, nodes, path=(), best=(None, None)):
        '''
        On each call we place the next node in either branch.
        To reduce memory usage we track only the path (successive indices) and best (lowest) area.
        '''
        depth = len(path)
        # prune if too many nodes on one side
        if path:
            remain = len(nodes) - depth
            size1 = sum(path)
            size0 = depth - size1
            if size0 + remain < self._min or size1 + remain < self._min:
                return best
        if depth == len(nodes):
            # we're done, so assess any improvement
            area = self._exact_area_sum(mbr0, mbr1)
            if best[0] is None or area < best[0]:
                best = (area, path)
        else:
            mbr = nodes[depth][0]
            best = self.__split_recursive(self._mbr_of_mbrs(mbr0, mbr) if mbr0 else mbr, mbr1, nodes, (*path, 0), best)
            best = self.__split_recursive(mbr0, self._mbr_of_mbrs(mbr1, mbr) if mbr1 else mbr, nodes, (*path, 1), best)
        return best

    def _split(self, height, nodes):
        '''
        Divide the nodes into two after considering all combinations.
        '''
        _, path = self.__split_recursive(None, None, nodes)
        mbrs_pair, nodes_pair = [None, None], [[], []]
        for i_node, i_pair in enumerate(path):
            node = nodes[i_node]
            mbr_pair = mbrs_pair[i_pair]
            mbr_node = node[0]
            if mbr_pair is None:
                mbr_pair = mbr_node
            else:
                mbr_pair = self._mbr_of_mbrs(mbr_pair, mbr_node)
            mbrs_pair[i_pair] = mbr_pair
            nodes_pair[i_pair].append(node)
        return [(mbrs_pair[0], (height, nodes_pair[0])), (mbrs_pair[1], (height, nodes_pair[1]))]


class CLRTree(LinearMixin, CartesianMixin, BaseTree): pass


class CQRTree(QuadraticMixin, CartesianMixin, BaseTree): pass


class CERTree(ExponentialMixin, CartesianMixin, BaseTree): pass


class LLRTree(LinearMixin, LatLonMixin, BaseTree): pass


class LQRTree(QuadraticMixin, LatLonMixin, BaseTree): pass


class LERTree(ExponentialMixin, LatLonMixin, BaseTree): pass
