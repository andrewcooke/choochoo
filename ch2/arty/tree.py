
from abc import ABC, abstractmethod
from enum import IntEnum


class MatchType(IntEnum):

    EQUAL = 0  # request exactly matches node
    CONTAINED = 1  # request contained in node
    CONTAINS = 2  # request contains node
    INTERSECT = 3  # request and node intersect


class BaseTree(ABC):

    # nodes in the tree are (height, data) where
    #   height = 0 for leaf nodes
    #   data is [(mbr, value), (mbr, value), ...] for leaf nodes
    #   data is [(mbr, children), (mbr, children), ...] for internal nodes
    #     where children is [(height, data), (height, data), ...]
    # the empty root is None

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

    def __init__(self, log, max_entries=4, min_entries=None):
        if not min_entries:
            min_entries = max_entries / 2
        if min_entries > max_entries / 2:
            raise Exception('Min number of entries in a node is too high')
        if min_entries < 1:
            raise Exception('Min number of entries in a node is too low')
        self._log = log
        self._max = max_entries
        self._min = min_entries
        self._root = None

    def get_point(self, x, y, match=MatchType.EQUAL):
        yield from self._get_normalized_mbr((x, y, x, y), match)

    def get_box(self, x1, y1, x2, y2, match=MatchType.EQUAL):
        yield from self._get_normalized_mbr(self._normalize_mbr(x1, y1, x2, y2), match)

    def _get_normalized_mbr(self, mbr, match):
        if self._root:
            yield from self._get_node(self._root, mbr, match)

    def _get_node(self, node, mbr, match):
        height, data = node
        for mbr_node, contents_node in data:
            if height:
                if (match in MatchType.EQUAL. MatchType.CONTAINED and self._contains(mbr_node, mbr)) or \
                        (match in MatchType.CONTAINS. MatchType.INTERSECT and self._intersect(mbr_node, mbr)):
                    yield from self._get_node(contents_node, mbr)
            else:
                if (match == MatchType.EQUAL and mbr == mbr_node) or \
                        (match == MatchType.CONTAINED and self._contains(mbr_node, mbr)) or \
                        (match == MatchType.CONTAINS and self._contains(mbr, mbr_node)) or \
                        (match == MatchType.INTERSECT and self._intersect(mbr, mbr_node)):
                    yield contents_node, mbr_node

    def add_point(self, value, x, y):
        '''
        Add value at a single point.
        '''
        self._add_normalized_mbr(0, value, (x, y, x, y))

    def add_box(self, value, x1, y1, x2, y2):
        '''
        Add value in a box.
        '''
        self._add_normalized_mbr(0, value, self._normalize_mbr(x1, y1, x2, y2))

    def _add_normalized_mbr(self, target, value, mbr):
        if self._root:
            if target > self._root[0]:
                raise Exception('Cannot add node at height t%d in tree of height %d' % (target, self._root[0]))
            split = self._add_node(self._root, target, value, mbr)
            if split:
                self._root = split
        else:
            if target:
                raise Exception('Cannot add node at height %d in empty tree' % target)
            self._root = (0, [(mbr, value)])

    def _add_node(self, node, target, value, mbr):
        height, data = node
        if height != target:
            i_best, area_best = self._best(data, mbr)
            child = data[i_best][1]
            data[i_best] = (area_best, child)
            split = self._add_node(child, target, value, mbr)
            if split:
                del data[i_best]
                data.extend(split[1])
                if len(data) <= self._max:
                    return None
                else:
                    return self._split(height, data)
        else:
            data.append((mbr, value))
            if len(data) <= self._max:
                return None
            else:
                return self._split(height, data)

    def _best(self, data, mbr):
        i_best, area_best, delta_area_best = None, None, None
        for i_child, (mbr_child, _) in enumerate(data):
            if self._intersect(mbr_child, mbr):
                if i_best is None:
                    i_best = i_child
                else:
                    if area_best is None:
                        mbr_best = data[i_best][0]
                        area_best = self._area(mbr_best)
                        delta_area_best = self._area(self._merge(mbr_best, mbr)) - area_best
                    area_child = self._area(mbr_child)
                    delta_area_child = self._area(self._merge(mbr_child, mbr)) - area_child
                    if delta_area_child < delta_area_best:
                        i_best, area_best, delta_area_best = i_child, area_child, delta_area_child
                    elif delta_area_child == delta_area_best:
                        if area_child < area_best:
                            i_best, area_best, delta_area_best = i_child, area_child, delta_area_child
        return i_best, area_best

    def delete_point(self, x, y, value=None, match=MatchType.EQUAL):
        return self._delete_normalized_mbr((x, y, x, y), value, match)

    def delete_box(self, x1, y1, x2, y2, value=None, match=MatchType.EQUAL):
        return self._delete_normalized_mbr(self._normalize_mbr(x1, y1, x2, y2), value, match)

    def _delete_normalized_mbr(self, mbr, value, match):
        count = 0
        for mbr in (mbr_found for (value_found, mbr_found) in self._get_normalized_mbr(mbr, match)
                    if value is None or value == value_found):
            # root cannot be empty as it contains mbr
            found = self._delete_node(self._root, mbr.pop(), value)
            if found:
                delete, inserts = found
                if delete:
                    self._root = None
                for insert in inserts:
                    self._add_normalized_mbr(*insert)
                count += 1
            else:
                raise Exception('Failed to delete %s' % mbr)
            if len(self._root[1]) == 1:  # single child
                self._root = self._root[1][0][1]  # contents of first child

    def _delete_node(self, node, mbr, value):
        height, data = node
        for i, (mbr_node, contents_node) in enumerate(data):
            if height:
                if self._contains(mbr_node, mbr):
                    found = self._delete_node(contents_node, mbr, value)
                    if found:
                        delete, inserts = found
                        if delete:
                            del data[i]
                            if len(data) < self._min:
                                for node in data:
                                    inserts.append((height, *node))
                                return True, inserts
                        else:
                            # something under data[i] has been deleted so recalculate mbr
                            old_mbr, (height_children, children) = data[i]
                            new_mbr = None
                            for (mbr_child, content) in children:
                                if new_mbr is None:
                                    new_mbr = mbr_child
                                else:
                                    new_mbr = self._intersect(new_mbr, mbr_child)
                            data[i] = (new_mbr, (height_children, children))
                        return False, inserts
            else:
                if mbr_node == mbr and (value is None or value == contents_node):
                    return True, []

    # allow different coordinate systems

    @abstractmethod
    def _normalize_mbr(self, x1, y1, x2, y2):
        raise NotImplementedError()

    @abstractmethod
    def _intersect(self, mbr1, mbr2):
        raise NotImplementedError()

    @abstractmethod
    def _contains(self, outer, inner):
        raise NotImplementedError()

    @abstractmethod
    def _area(self, mbr):
        raise NotImplementedError()

    @abstractmethod
    def _merge(self, mbr1, mbr2):
        raise NotImplementedError()

    # allow different split algorithms

    @abstractmethod
    def _pick_linear_seeds(self, data):
        raise NotImplementedError()

    @abstractmethod
    def _split(self, height, data):
        raise NotImplementedError()


class CartesianMixin:

    def _normalize_mbr(self, x1, y1, x2, y2):
        '''
        return xy_bottom_left, xy_top_right for cartesian coordinates.
        '''
        return min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)

    def _intersect(self, mbr1, mbr2):
        x1, y1, x2, y2 = mbr1
        X1, Y1, X2, Y2 = mbr2
        return x1 <= X2 and x2 >= X1 and y1 <= Y2  and y2 >= Y1

    def _contains(self, outer, inner):
        x1, y1, x2, y2 = outer
        X1, Y1, X2, Y2 = inner
        return x1 <= X1 and x2 >= x2 and y1 <= Y1 and y2 >= Y2

    def _area(self, mbr):
        x1, y1, x2, y2 = mbr
        return (x2 - x1) * (y2 - y1)

    def _merge(self, mbr1, mbr2):
        x1, y1, x2, y2 = mbr1
        X1, Y1, X2, Y2 = mbr2
        return min(x1, X1), min(y1, Y1), max(x2, X2), max(y2, Y2)

    def __extremes(self, data):
        index, extreme = None, None
        for i, (mbr, _) in enumerate(data):
            if not i:
                index = [0, 0, 0 ,0]
                extreme = mbr
            else:
                for j in range(2):
                    if mbr[j] < extreme[j]:
                        extreme[j] = mbr[j]
                        index[j] = i
                    if mbr[j+2] > extreme[j+2]:
                        extreme[j+2] = mbr[j+2]
                        index[j+2] = i
        return index, extreme

    def _pick_linear_seeds(self, data):
        _, extreme = self.__extremes(self._root[1])
        norm_x, norm_y = extreme[2] - extreme[0], extreme[3] - extreme[1]
        norm = [norm_x, norm_y, norm_x, norm_y]
        index, extreme = self.__extremes(data)
        extreme = [x / n for x, n in zip(extreme, norm)]
        if extreme[2] - extreme[0] > extreme[3] - extreme[1]:
            return index[0], index[2]
        else:
            return index[1], index[3]


class LinearSplitMixin:

    def _split(self, height, data):
        i, j = self._pick_linear_seeds(data)
        a, b = [data[i]], [data[j]]
        del data[max(i, j)]
        del data[min(i, j)]
        while data:
            a.append(data.pop())
            if data:
                b.append(data.pop())
        return height+1, (height, a), (height, b)


class CLRTree(BaseTree, LinearSplitMixin, CartesianMixin): pass

