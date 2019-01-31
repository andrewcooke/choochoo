
from abc import ABC, abstractmethod
from enum import IntEnum


class MatchType(IntEnum):
    '''
    Control how MBRs are matched.
    '''

    EQUALS = 0  # request exactly equal to node
    CONTAINED = 1  # request contained in node
    CONTAINS = 2  # request contains node
    OVERLAP = 3  # request and node overlap


class BaseTree(ABC):

    # nodes in the tree are
    #   (height, [entry, entry, entry...])
    #     entry is (mbr, content)
    #       content is node if height > 0
    #                  (points, value) if height = 0
    # note that nodes and entries are different

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

    def __init__(self, items=None, *, max_entries=3, min_entries=None,
                 subtrees_flag=True, default_match=MatchType.EQUALS, default_border=0):
        '''
        Create an empty tree.

        `items` allows construction from an iterable of `(points, value)` pairs
        (as returned by `.items()`),

        `max_entries` is the maximum number of children a node can have.
        This data structure was originally designed for mass storage, where such a parameter is important.
        For in-memory use, a smaller value gives more branching, reduced comparisons, and better performance.

        `subtrees_flag` enables insertion of entire subtrees (rather than leaves) during internal balancing.
        It seems to be what is described in the original paper and gives a small speedup in some cases.
        '''
        if not min_entries:
            min_entries = max_entries // 2
        if min_entries > max_entries // 2:
            raise Exception('Min number of entries in a node is too high')
        if min_entries < 1:
            raise Exception('Min number of entries in a node is too low')
        self.__max_entries = max_entries
        self.__min_entries = min_entries
        self.__subtrees_flag = subtrees_flag
        self.__default_match = default_match
        self.__default_border = default_border
        self.__root = (0, [])
        self.__size = 0
        self.__hash = 966038070
        self.add_all(items)

    @property
    def global_mbr(self):
        if self.__size:
            x1, y1, x2, y2 = self._mbr_of_entries(*self.__root[1])
            x1, y1 = self._denormalize_point((x1, y1))
            x2, y2 = self._denormalize_point((x2, y2))
            return x1, y1, x2, y2
        else:
            return None

    @property
    def min_entries(self):
        return self.__min_entries

    @property
    def max_entries(self):
        return self.__max_entries

    @property
    def height(self):
        return self.__root[0]

    def size(self):
        return self.__size

    def _check_points(self, points):
        try:
            _ = points[0][0]
        except Exception:
            raise Exception('The `points` argument is a sequence of (x, y) points. ' +
                            'You may have entered a single (x, y) point.')

    def get(self, points, value=None, match=None, border=None):
        '''
        An iterator over values of nodes that match the MBR for the given points.

        The `match` describes the kind of matching done.

        If `value` is given then only nodes with that value are found.

        `border` is added to the MBR (eg to account for errors).
        '''
        self._check_points(points)
        match = self.__default_match if match is None else match
        border = self.__default_border if border is None else border
        points = self._normalize_points(points)
        mbr_request = self._mbr_of_points(points, border=border)
        content_request = (points, value)
        for points_entry, value_entry in self.__get_leaf_contents(self.__root, mbr_request, content_request, match):
            yield value_entry

    def get_items(self, points, value=None, match=None, border=None):
        '''
        An iterator over (MBR, value) of nodes that match the MBR for the given points.

        The `match` describes the kind of matching done.

        If `value` is given then only nodes with that value are found.

        `border` is added to the MBR (eg to account for errors).
        '''
        self._check_points(points)
        match = self.__default_match if match is None else match
        border = self.__default_border if border is None else border
        points = self._normalize_points(points)
        mbr_request = self._mbr_of_points(points, border=border)
        content_request = (points, value)
        for points_entry, value_entry in self.__get_leaf_contents(self.__root, mbr_request, content_request, match):
            yield self._denormalize_points(points_entry), value_entry

    def __get_leaf_contents(self, node, mbr_request, content_request, match):
        '''
        Internal get from node.
        '''
        height, entries = node
        for mbr_entry, content_entry in entries:
            if height:
                if self.__descend(mbr_request, mbr_entry, match):
                    yield from self.__get_leaf_contents(content_entry, mbr_request, content_request, match)
            elif self.__match(mbr_request, mbr_entry, content_request, content_entry, match):
                yield content_entry

    def __descend(self, mbr_request, mbr_entry, match):
        '''
        Descend in search?
        '''
        return (match in (MatchType.EQUALS, MatchType.CONTAINED) and self._contains(mbr_entry, mbr_request)) or \
               (match in (MatchType.CONTAINS, MatchType.OVERLAP) and self._overlaps(mbr_entry, mbr_request))

    def __match(self, mbr_request, mbr_entry, content_request, content_entry, match):
        '''
        Match search?
        '''
        points_node, value_node = content_entry
        points_request, value_request = content_request
        return (value_request is None or value_request == value_node) and (
                (match == MatchType.EQUALS and points_request == points_node) or
                (match == MatchType.CONTAINED and self._contains(mbr_entry, mbr_request)) or
                (match == MatchType.CONTAINS and self._contains(mbr_request, mbr_entry)) or
                (match == MatchType.OVERLAP and self._overlaps(mbr_request, mbr_entry)))

    def add(self, points, value, border=None):
        '''
        Add a value at the MBR of the given points.

        `border` is added to the MBR (eg to account for errors).
        '''
        self._check_points(points)
        border = self.__default_border if border is None else border
        points = self._normalize_points(points)
        mbr_addition = self._mbr_of_points(points, border=border)
        content = (points, value)
        self.__add_to_root(0, mbr_addition, content)
        self.__update_state(1, content)

    def add_all(self, items, border=None):
        '''
        Add a sequence of (point, value) pairs.

        `border` is added to the MBR (eg to account for errors).
        '''
        if items:
            for points, value in items:
                self.add(points, value, border=border)

    def __update_state(self, delta, content):
        '''
        Update size and hash.
        '''
        self.__size += delta
        self.__hash ^= hash(content)

    def __add_to_root(self, target, mbr_addition, content):
        '''
        Internal add at root (handling split has different logic to other nodes).

        `target` is the height for insertion.  This allows for subtrees to be re-inserted as a whole.
        '''
        split = self.__add_to_node(self.__root, target, mbr_addition, content)
        if split:
            height = split[0][1][0] + 1
            self.__root = (height, split)

    def __add_to_node(self, node, target, mbr_addition, content):
        '''
        Internal add at node.

        `target` is the height for insertion.  This allows for subtrees to be re-inserted as a whole.
        '''
        height, entries = node
        if height != target:
            i_best, mbr_best = self._best(entries, mbr_addition, height)
            child = entries[i_best][1]
            # optimistically set mbr on way down (since we have the mbr); will be removed if split spills data over
            entries[i_best] = (mbr_best, child)
            split = self.__add_to_node(child, target, mbr_addition, content)
            if split:
                del entries[i_best]
                entries.extend(split)
        else:
            entries.append((mbr_addition, content))
        # at this point parent mbr still correct (set on way down)
        if len(entries) > self.__max_entries:
            return self._split(height, entries)

    def _best(self, entries, mbr, height):
        '''
        Given a list of nodes, find the node whose area increases least when the given MBR is added.

        Not private because accessed by split mixins.
        '''
        i_best, mbr_best, area_best, delta_area_best, len_best = None, None, None, None, None
        for i_child, (mbr_entry, content_entry) in enumerate(entries):
            if i_best is None:
                i_best = i_child
                mbr_best = self._mbr_of_mbrs(mbr_entry, mbr)
                area_best = self._area_of_mbr(mbr_best)
                delta_area_best = self._area_of_mbr(mbr_best) - self._area_of_mbr(mbr_entry)
                len_best = len(content_entry[1]) if content_entry[0] else 0
            else:
                mbr_merge = self._mbr_of_mbrs(mbr_entry, mbr)
                area_merge = self._area_of_mbr(mbr_merge)
                delta_area_merge = area_merge - self._area_of_mbr(mbr_entry)
                if delta_area_merge < delta_area_best or \
                        (delta_area_merge == delta_area_best and area_merge < area_best) or \
                        (delta_area_merge == delta_area_best and area_merge == area_best and
                         height and len(entries) < len_best):
                    i_best, mbr_best, area_best, delta_area_best, len_best = \
                        i_child, mbr_merge, area_merge, delta_area_merge, \
                        len(content_entry[1]) if content_entry[0] else 0
        return i_best, mbr_best

    def delete(self, points, value=None, match=None, border=None):
        '''
        Remove entries that match the MBR of the given points and optional value.

        `border` is added to the MBR (eg to account for errors).
        '''
        self._check_points(points)
        match = self.__default_match if match is None else match
        border = self.__default_border if border is None else border
        points = self._normalize_points(points)
        mbr_deletion = self._mbr_of_points(points, border=border)
        content_deletion = (points, value)
        count = 0
        try:
            while True:
                self.__delete_one_from_root(mbr_deletion, content_deletion, match)
                count += 1
        except KeyError:
            return count

    def delete_one(self, points, value=None, match=None, border=None):
        '''
        Remove a single entry that match the MBR of the given points and optional value.

        Raises `KeyError` if no entry exists.

        `border` is added to the MBR (eg to account for errors).
        '''
        self._check_points(points)
        match = self.__default_match if match is None else match
        border = self.__default_border if border is None else border
        points = self._normalize_points(points)
        mbr_deletion = self._mbr_of_points(points, border=border)
        content_deletion = (points, value)
        self.__delete_one_from_root(mbr_deletion, content_deletion, match)

    def __delete_one_from_root(self, mbr_deletion, content_deletion, match):
        '''
        Internal deletion from root (handling deletion of a node has different logic to internal nodes).
        '''
        found = self.__delete_one_from_node(self.__root, mbr_deletion, content_deletion, match, 2)
        if found:
            delete, inserts, content_found = found
            if delete:
                self.__root = (0, [])
            self.__reinsert(inserts)
            if len(self.__root[1]) == 1 and self.height:  # single child, not leaf
                self.__root = self.__root[1][0][1]  # contents of first child
            self.__update_state(-1, content_found)
        else:
            points, value = content_deletion
            raise KeyError('Failed to delete %s%s' % (points, '' if value is None else ' (value %s)' % value))

    def __delete_one_from_node(self, node, mbr_deletion, content_deletion, match, local_min):
        '''
        Internal deletion from node.
        '''
        height, entries = node
        for i, (mbr_entry, contents_entry) in enumerate(entries):
            if height:
                if self.__descend(mbr_deletion, mbr_entry, match):
                    found = self.__delete_one_from_node(contents_entry, mbr_deletion, content_deletion, match,
                                                        self.__min_entries)
                    if found:
                        delete, inserts, content_found = found
                        if delete:
                            del entries[i]
                            if len(entries) < local_min:
                                inserts.extend((height, entry) for entry in entries)
                                return True, inserts, content_found
                        else:
                            # something under entries[i] has been deleted so recalculate mbr
                            _, (height_children, entries_children) = entries[i]
                            new_mbr = self._mbr_of_entries(*entries_children)
                            entries[i] = (new_mbr, (height_children, entries_children))
                        return False, inserts, content_found
            elif self.__match(mbr_deletion, mbr_entry, content_deletion, contents_entry, match):
                del entries[i]
                if len(entries) < local_min:
                    return True, [(height, entry) for entry in entries], contents_entry
                else:
                    return False, [], contents_entry

    def __leaves(self, node, canary=True):
        '''
        Iterator over the leaves in a node.
        '''
        if canary is True:
            canary = self.__hash
        height, entries = node
        for mbr_entry, content_entry in entries:
            if canary is not False and canary != self.__hash:
                raise RuntimeError('Tree was mutated while iterating over contents')
            if height:
                yield from self.__leaves(content_entry, canary=canary)
            else:
                yield mbr_entry, content_entry

    def __reinsert(self, inserts):
        '''
        Reinsert sub-trees (including leaves) removed during re-arrangement on deletion.

        We try to insert whole sub-trees, but this is not always possible (if the height has changed).
        '''
        max_height = self.height
        for (height_entry, (mbr_entry, content_entry)) in inserts:
            if height_entry and (height_entry > max_height or not self.__subtrees_flag):
                # can't (or won't) add the entire tree, so re-add the leaves
                for mbr_leaf, content_leaf in self.__leaves(content_entry, False):
                    self.__add_to_root(0, mbr_leaf, content_leaf)
            else:
                self.__add_to_root(height_entry, mbr_entry, content_entry)

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
        for mbr, (points, value) in self.__leaves(self.__root):
            yield self._denormalize_points(points)

    def values(self):
        '''
        All values.
        '''
        for mbr, (points, value) in self.__leaves(self.__root):
            yield value

    def items(self):
        '''
        All (points, value) pairs.
        '''
        for mbr, (points, value) in self.__leaves(self.__root):
            yield (points, value)

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

    def __str__(self):
        return '%s RTree (%s leaves, %d height, %d-%d entries)' % \
               (self.split_algorithm, len(self), self.height, self.min_entries, self.max_entries)

    # utilities for debugging

    def dump(self):
        '''
        An iterator over the tree structure.
        '''
        height, entries = self.__root
        yield height + 1, self._mbr_of_entries(*entries), None  # implied mbr on all nodes
        yield from self._dump_node(self.__root)

    def _dump_node(self, node):
        '''
        Internal iterator over the tree structure.
        '''
        height, entries = node
        for mbr, content in entries:
            if height:
                yield height, mbr, None
                yield from self._dump_node(content)
            else:
                yield height, mbr, content

    def print(self):
        '''
        Dump the tree structure to stdout for debugging.
        '''
        for height, mbr, content in self.dump():
            print('%2d %s %s %s' %
                  (height, ' ' * (10 - height), mbr, '' if content is None else content))

    def assert_consistent(self):
        '''
        Make some basic tests of consistency.
        '''
        if self.__size and not self.__root[1]:
            raise Exception('Emtpy root (and size %d)' % self.__size)
        size = self._assert_consistent(self.__root)
        if size != self.__size:
            raise Exception('Unexpected number of leaves (%d != %d)' % (size, self.__size))

    def _assert_consistent(self, node):
        '''
        Internal tests of consistency.
        '''
        if node:
            height, entries = node
            if len(entries) < self.__min_entries and node != self.__root:
                raise Exception('Too few children at height %d' % height)
            if len(entries) > self.__max_entries:
                raise Exception('Too many children at height %d' % height)
            if height:
                count = 0
                for mbr_entry, content_entry in entries:
                    height_entry, entries_entry = content_entry
                    mbr_check = self._mbr_of_entries(*entries_entry)
                    if mbr_check != mbr_entry:
                        raise Exception('Bad MBR at height %d %s / %s' % (height, mbr_check, mbr_entry))
                    count += self._assert_consistent(content_entry)
                return count
            else:
                return len(entries)
        else:
            return 0

    # allow different coordinate systems
    # nothing above should depend on the exact representation of point or mbr

    @property
    @abstractmethod
    def split_algorithm(self):
        raise NotImplementedError()

    def _normalize_points(self, points):
        return tuple(self._normalize_point(p) for p in points)

    @abstractmethod
    def _normalize_point(self, point):
        raise NotImplementedError()

    def _denormalize_points(self, points):
        return tuple(self._denormalize_point(p) for p in points)

    def _denormalize_point(self, point):
        return point

    @abstractmethod
    def _mbr_of_points(self, points, border=0):
        raise NotImplementedError()

    def _mbr_of_entries(self, *entries):
        return self._mbr_of_mbrs(*(mbr for mbr, _ in entries))

    @abstractmethod
    def _mbr_of_mbrs(self, *mbrs):
        raise NotImplementedError()

    @abstractmethod
    def _overlaps(self, mbr1, mbr2):
        raise NotImplementedError()

    @abstractmethod
    def _contains(self, outer, inner):
        raise NotImplementedError()

    @abstractmethod
    def _area_of_mbr(self, mbr):
        raise NotImplementedError()

    # allow different split algorithms

    @abstractmethod
    def _split(self, height, entries):
        raise NotImplementedError()

    @abstractmethod
    def _pick_seeds(self, entries):
        raise NotImplementedError()

    @abstractmethod
    def _pick_next(self, pair, entries):
        raise NotImplementedError()


class CartesianMixin:
    '''
    Basic support for (x,y) points..
    '''

    def _normalize_point(self, point):
        '''
        No normalizetion by default.
        '''
        return point

    def _mbr_of_points(self, points, border=0):
        '''
        Find the MBR of a set of points,
        '''
        xs, ys = zip(*points)
        return min(xs) - border, min(ys) - border, max(xs) + border, max(ys) + border

    def _mbr_of_mbrs(self, *mbrs):
        '''
        Find the MBR of a set of MBRs.
        '''
        x1s, y1s, x2s, y2s = zip(*mbrs)
        return min(x1s), min(y1s), max(x2s), max(y2s)

    def _overlaps(self, mbr1, mbr2):
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

    def _area_of_mbr(self, mbr):
        '''
        Area of the MBR
        '''
        x1, y1, x2, y2 = mbr
        return (x2 - x1) * (y2 - y1)

    def __extremes(self, entries):
        '''
        Internal routine for linear seeds.

        Measure the lowest higher bound, left-most right bound, etc, from a collection of MBRs
        and records which MRB (index) is responsible for each.
        '''
        index, extreme = None, None
        for i, (mbr, _) in enumerate(entries):
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

    def _pick_seeds(self, entries):
        '''
        Choose the two MBRs that are furthest apart.

        Only called from LinearSplitMixin.
        '''
        global_mbr = self.global_mbr
        norm_x, norm_y = global_mbr[2] - global_mbr[0], global_mbr[3] - global_mbr[1]
        norm = [norm_x, norm_y, norm_x, norm_y]
        index, extremes = self.__extremes(entries)
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
            return self._area_of_mbr(mbr1)
        elif not mbr1:
            return self._area_of_mbr(mbr0)
        else:
            outer = self._area_of_mbr(mbr0) + self._area_of_mbr(mbr1)
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
    '''
    Normalize (lon, lat) so that "wrapping" in longitude is not possible unless it varies by 180 degrees.
    '''

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
        Revert the normalization above.
        '''
        lon, lat = point
        lon = self._normalize_angle(lon + self.__zero_lon)
        return lon, lat


class LinearMixin:
    '''
    Simple node selection.
    '''

    @property
    def split_algorithm(self):
        return 'Linear'

    def _split(self, height, entries):
        '''
        Divide the entries into two,
        '''
        i, j = self._pick_seeds(entries)
        split = [(entries[i][0], (height, [entries[i]])), (entries[j][0], (height, [entries[j]]))]
        del entries[max(i, j)]
        del entries[min(i, j)]
        # indexing ugliness below is rebuilding tuple with new mbr
        while entries:
            if len(entries) < self.min_entries:
                for index in 0, 1:
                    split_entries = split[index][1][1]
                    if len(split_entries) + len(entries) == self.min_entries:
                        split_entries.extend(entries)
                        split[index] = (self._mbr_of_entries(*split_entries), split[index][1])
                        return split
            node, entries = self._pick_next(split, entries)
            index, mbr = self._best(split, node[0], height)
            split[index] = (mbr, split[index][1])
            split[index][1][1].append(node)
        return split

    # _pick_seeds is on CartesianMixin because it's not abstracted from the coord system.

    def _pick_next(self, pair, entries):
        entry = entries.pop()
        return entry, entries


class QuadraticMixin(LinearMixin):
    '''
    This does a better job of grouping nodes (than linear) and is not measurably slower.
    '''

    @property
    def split_algorithm(self):
        return 'Quadratic'

    def _pick_seeds(self, entries):
        n, area_delta_best, best = len(entries), None, None
        for i in range(n):
            mbr_i = entries[i][0]
            for j in range(i):
                mbr_j = entries[j][0]
                mbr_both = self._mbr_of_mbrs(mbr_i, mbr_j)
                area_delta = self._area_of_mbr(mbr_both) - self._area_of_mbr(mbr_i) - self._area_of_mbr(mbr_j)
                if area_delta_best is None or area_delta > area_delta_best:
                    area_delta_best, best = area_delta, (i, j)
        return best

    def _pick_next(self, pair, entries):
        area_delta_best, best = None, None
        for i in range(len(entries)):
            area_delta = abs((self._area_of_mbr(self._mbr_of_entries(entries[i], pair[0])) - self._area_of_mbr(pair[0][0])) -
                             (self._area_of_mbr(self._mbr_of_entries(entries[i], pair[1])) - self._area_of_mbr(pair[1][0])))
            if area_delta_best is None or area_delta > area_delta_best:
                area_delta_best, best = area_delta, i
        node = entries[best]
        del entries[best]
        return node, entries


class ExponentialMixin:
    '''
    Pick nodes by making a complete comparison of all possibilities.
    '''

    @property
    def split_algorithm(self):
        return 'Exponential'

    def _pick_next(self, pair, nodes):
        # avoid ABC error
        raise NotImplementedError()

    def _pick_seeds(self, nodes):
        # avoid ABC error
        raise NotImplementedError()

    # _exact_area_sum() is on CartesianMixin because it is not abstracted from the coordinate system.

    def __split_recursive(self, mbr0, mbr1, entries, path=(), best=(None, None)):
        '''
        On each call we place the next node in either branch.
        To reduce memory usage we track only the path (successive indices) and best (lowest) area.
        '''

        # prune if too many nodes on one side
        depth = len(path)
        if path:
            remain = len(entries) - depth
            size1 = sum(path)
            size0 = depth - size1
            if size0 + remain < self.min_entries or size1 + remain < self.min_entries:
                return best

        if depth == len(entries):
            # we're done, so assess any improvement
            area = self._exact_area_sum(mbr0, mbr1)
            if best[0] is None or area < best[0]:
                best = (area, path)
        else:
            mbr = entries[depth][0]
            best = self.__split_recursive(self._mbr_of_mbrs(mbr0, mbr) if mbr0 else mbr, mbr1, entries, (*path, 0), best)
            best = self.__split_recursive(mbr0, self._mbr_of_mbrs(mbr1, mbr) if mbr1 else mbr, entries, (*path, 1), best)
        return best

    def _split(self, height, entries):
        '''
        Divide the nodes into two after considering all combinations.
        '''
        _, path = self.__split_recursive(None, None, entries)
        mbrs_pair, entries_pair = [None, None], [[], []]
        for i_node, i_pair in enumerate(path):
            node = entries[i_node]
            mbr_pair = mbrs_pair[i_pair]
            mbr_node = node[0]
            if mbr_pair is None:
                mbr_pair = mbr_node
            else:
                mbr_pair = self._mbr_of_mbrs(mbr_pair, mbr_node)
            mbrs_pair[i_pair] = mbr_pair
            entries_pair[i_pair].append(node)
        return [(mbrs_pair[0], (height, entries_pair[0])), (mbrs_pair[1], (height, entries_pair[1]))]


class CLRTree(LinearMixin, CartesianMixin, BaseTree): pass


class CQRTree(QuadraticMixin, CartesianMixin, BaseTree): pass


class CERTree(ExponentialMixin, CartesianMixin, BaseTree): pass


class LLRTree(LinearMixin, LatLonMixin, BaseTree): pass


class LQRTree(QuadraticMixin, LatLonMixin, BaseTree): pass


class LERTree(ExponentialMixin, LatLonMixin, BaseTree): pass


