
from math import sqrt
from random import uniform, gauss, seed, randrange
from time import time

from ch2.arty.tree import CLRTree, MatchType, CQRTree, CERTree, LQRTree


def known_points(tree):
    tree.add([(0, 0)], '0')
    tree.add([(0, 1)], 'y')
    tree.add([(1, 0)], 'x')
    tree.add([(1, 1)], '1')
    assert len(tree) == 4, len(tree)
    all = list(tree.get([(0, 0), (1, 1)], match=MatchType.CONTAINS))
    assert len(all) == 4, all
    some = list(tree.get([(0, 0), (0, 1)], match=MatchType.CONTAINS))
    assert len(some) == 2, some
    some = list(tree.get([(0, 0), (0, 1)], match=MatchType.CONTAINED))
    assert len(some) == 0, some
    some = list(tree.get([(0, 0), (0, 1)], match=MatchType.EQUAL))
    assert len(some) == 0, some
    assert len(tree) == 4, len(tree)
    tree.delete([(0, 0)])
    assert len(tree) == 3, len(tree)
    some = list(tree.get([(0, 0), (0, 1)], match=MatchType.CONTAINS))
    assert len(some) == 1, some


def test_known_points():
    known_points(CLRTree(2))
    known_points(CLRTree())
    known_points(CQRTree(2))
    known_points(CQRTree())
    known_points(CERTree(2))
    known_points(CERTree())


def known_boxes(tree):
    tree.add([(-0.1, -0.1), (0.1, 0.1)], '0')
    tree.add([(0.9, 0.9), (1.1, 1.1)], '1')
    tree.add([(0, 0), (1, 1)], 'sq')
    tree.add([(2, 2), (3, 3)], 'x')
    some = list(tree.get([(0, 0), (1, 1)], match=MatchType.CONTAINED))
    assert len(some) == 1, some
    some = list(tree.get([(0, 0), (1, 1)], match=MatchType.CONTAINS))
    assert len(some) == 1, some
    some = list(tree.get([(0, 0), (2, 1)], match=MatchType.CONTAINED))
    assert len(some) == 0, some
    some = list(tree.get([(0, 0), (2, 1)], match=MatchType.CONTAINS))
    assert len(some) == 1, some
    some = list(tree.get([(0, 0), (1, 1)], match=MatchType.INTERSECTS))
    assert len(some) == 3, some


def test_known_boxes():
    known_boxes(CLRTree(2))
    known_boxes(CLRTree())
    known_boxes(CQRTree(2))
    known_boxes(CQRTree())
    known_points(CERTree(2))
    known_points(CERTree())


def test_delete_points():

    for size in 2, 3, 4, 8:

        def new_tree():
            tree = CQRTree(size)
            for i in range(4):
                for j in range(4):
                    tree.add([(i, j)], i+j)
            assert len(tree) == 16
            return tree

        tree = new_tree()
        tree.delete([(1, 2)])
        assert len(tree) == 15, len(tree)

        tree = new_tree()
        tree.delete([(1, 1), (2, 2)])
        assert len(tree) == 16, len(tree)  # default is EQUALS
        tree = new_tree()
        tree.delete([(1, 1), (2, 2)], match=MatchType.CONTAINS)
        assert len(tree) == 12, len(tree)
        tree = new_tree()
        tree.delete([(1, 1), (2, 2)], match=MatchType.CONTAINED)
        assert len(tree) == 16, len(tree)


def random_box(n, size):
    x = uniform(0, size)
    y = uniform(0, size)
    dx = gauss(0, size/sqrt(n))
    dy = gauss(0, size/sqrt(n))
    return [(x, y), (x + dx, y + dy)]


def gen_random(n, size=100):
    for i in range(n):
        yield 1, random_box(n, size=size)


def test_equals():
    for size in 2, 3, 4, 8:
        tree1 = CQRTree(size)
        for i, box in gen_random(10):
            tree1.add(box, i)
        tree2 = CQRTree(size)
        for k, v in tree1.items():
            tree2.add(k, v)
        assert tree1 == tree2


def test_underscores():
    for size in 2, 3, 4, 8:
        tree1 = CQRTree(size)
        for i, box in gen_random(10):
            tree1[box] = i
        tree2 = CQRTree(size)
        for k, v in tree1.items():
            tree2.add(k, v)
        assert tree1 == tree2


def best_bug(tree):
    for i, (value, box) in enumerate(gen_random(100)):
        tree.add(box, value % 10)
        tree.assert_consistent()


def test_best_bug():
    seed(4)  # 1:46 2:17 3:56 4:8 5:10 6:16 7:58 8:8
    best_bug(CLRTree(2))
    best_bug(CQRTree(2))
    best_bug(CERTree(2))


def stress(type, n_children, n_data, check=True):
    seed(1)
    tree = type(n_children)
    data = list(gen_random(n_data))

    for value, box in data:
        tree.add(box, value)
        if check:
            tree.assert_consistent()

    for i in range(100):

        n_delete = randrange(int(1.1 * n_data))   # delete to empty 10% of time
        for j in range(n_delete):
            if data:
                index = randrange(len(data))
                value, box = data[index]
                del data[index]
                tree.delete_one(box, value=value)
                if check:
                    tree.assert_consistent()
            else:
                assert not tree, tree

        while len(data) < n_data:
            value, box = next(gen_random(1))
            data.append((value, box))
            tree.add(box, value)
            if check:
                tree.assert_consistent()


def test_stress():
    for type in CLRTree, CQRTree, CERTree:
        print('type %s' % type)
        for n_children in 3, 4, 10:
            print('n_children %d' % n_children)
            for n_data in 1, 2, 3:#, 100:
                print('n_data %d' % n_data)
                stress(type, n_children, n_data)


def test_latlon():
    tree = LQRTree()
    for lon in -180, 180:
        tree.add([(lon, 0)], str(lon))
    for lon in -180, 180:
        found = list(tree.get([(lon, 0)]))
        assert len(found) == 2, found
    area = tree._area(tree._normalize_mbr([(-179, -1), (179, 1)]))
    assert area == 4, area


def measure(tree, n_data, n_loops, dim=100):

    seed(1)
    data = list(gen_random(n_data, size=dim))

    start = time()
    for i in range(n_loops):
        for value, box in data:
            tree[box] = value
        assert len(tree) == len(data), len(tree)
        for _, box in data:
            list(tree[box])
        for value, box in data:
            del tree[box]
        assert len(tree) == 0

    return time() - start


def measure_sizes():
    for type in CLRTree, CQRTree, CERTree:
        print()
        for size in 2, 4, 6, 8, 10, 16, 32, 64, 128:
            t = measure(type(size), 1000, 2)
            print('%s %d %s' % (type, size, t))
            if t > 5 and size > 4:
                print('abort')
                break


# for profiling
if __name__ == '__main__':
    stress(CQRTree, 8, 100, check=False)
