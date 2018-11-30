
from math import sqrt
from random import uniform, gauss, seed, randrange
from time import time

from ch2.arty.tree import CLRTree, MatchType


def test_cl_known_points():

    tree = CLRTree(2)
    tree.add_point('0', 0, 0)
    tree.add_point('y', 0, 1)
    tree.add_point('x', 1, 0)
    tree.add_point('1', 1, 1)
    assert len(tree) == 4, len(tree)
    all = list(tree.get_box(0, 0, 1, 1, match=MatchType.CONTAINS))
    assert len(all) == 4, all
    some = list(tree.get_box(0, 0, 0, 1, match=MatchType.CONTAINS))
    assert len(some) == 2, some
    some = list(tree.get_box(0, 0, 0, 1, match=MatchType.CONTAINED))
    assert len(some) == 0, some
    some = list(tree.get_box(0, 0, 0, 1, match=MatchType.EQUAL))
    assert len(some) == 0, some
    tree.delete_point(0, 0)
    assert len(tree) == 3, len(tree)
    some = list(tree.get_box(0, 0, 0, 1, match=MatchType.CONTAINS))
    assert len(some) == 1, some


def test_cl_known_regions():

    tree = CLRTree(2)
    tree.add_box('0', -0.1, -0.1, 0.1, 0.1)
    tree.add_box('1', 0.9, 0.9, 1.1, 1.1)
    tree.add_box('sq', 0, 0, 1, 1)
    tree.add_box('x', 2, 2, 3, 3)
    some = list(tree.get_box(0, 0, 1, 1, match=MatchType.CONTAINED))
    assert len(some) == 1, some
    some = list(tree.get_box(0, 0, 1, 1, match=MatchType.CONTAINS))
    assert len(some) == 1, some
    some = list(tree.get_box(0, 0, 2, 1, match=MatchType.CONTAINED))
    assert len(some) == 0, some
    some = list(tree.get_box(0, 0, 2, 1, match=MatchType.CONTAINS))
    assert len(some) == 1, some
    some = list(tree.get_box(0, 0, 1, 1, match=MatchType.INTERSECT))
    assert len(some) == 3, some


def random_box(n, size):
    x = uniform(0, size)
    y = uniform(0, size)
    dx = gauss(0, size/sqrt(n))
    dy = gauss(0, size/sqrt(n))
    return x, y, x + dx, y + dy


def gen_random(n, size=100):
    for i in range(n):
        yield i, random_box(n, size=size)


def test_best_bug():
    seed(4)  # 1:46 2:17 3:56 4:8 5:10 6:16 7:58 8:8
    tree = CLRTree(2)
    for i, (value, box) in enumerate(gen_random(100)):
        tree.add_box(value % 10, *box)
        tree.assert_consistent()


def test_stress():

    for n_children in 3, 4, 10:
        print('n_children %d' % n_children)

        for n_data in 1, 2, 3, 100:
            print('n_data %d' % n_data)

            seed(1)
            tree = CLRTree(n_children)
            data = list(gen_random(n_data))

            for value, box in data:
                tree.add_box(value, *box)
                tree.assert_consistent()

            for i in range(100):

                n_delete = randrange(n_data)
                for j in range(n_delete):
                    if data:
                        index = randrange(len(data))
                        value, box = data[index]
                        del data[index]
                        tree.delete_box(*box, value=value)
                        tree.assert_consistent()

                while len(data) < n_data:
                    value, box = next(gen_random(1))
                    data.append((value, box))
                    tree.add_box(value, *box)
                    tree.assert_consistent()


def measure(tree, n_data, n_loops, n_read, size=100):
    seed(1)
    data = list(gen_random(n_data, size=size))

    start = time()
    for value, box in data:
        tree.add_box(value, *box)
    for i in range(n_loops):
        n_delete = randrange(n_data)
        for j in range(n_delete):
            if data:
                index = randrange(len(data))
                value, box = data[index]
                del data[index]
                tree.delete_box(*box, value=value)
        while len(data) < n_data:
            value, box = next(gen_random(1))
            data.append((value, box))
            tree.add_box(value, *box)
        for _ in range(n_read):
            tree.get_box(*random_box(n_data, size=size))

    return time() - start


def measure_sizes():
    for size in 2, 4, 8, 16, 32, 64, 128, 2:
        print('%d %s' % (size, measure(CLRTree(size), 1000, 10, 1000)))
