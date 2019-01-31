
from math import sqrt
from random import uniform, gauss, seed, randrange
from time import time
from unittest import TestCase

from ch2.arty.spherical import Global
from ch2.arty.tree import CLRTree, MatchType, CQRTree, CERTree, LQRTree


class TestArty(TestCase):

    def known_points(self, tree):
        tree.add([(0, 0)], '0')
        tree.add([(0, 1)], 'y')
        tree.add([(1, 0)], 'x')
        tree.add([(1, 1)], '1')
        self.assertEqual(len(tree), 4)
        all = list(tree.get([(0, 0), (1, 1)], match=MatchType.CONTAINS))
        self.assertEqual(len(all), 4)
        some = list(tree.get([(0, 0), (0, 1)], match=MatchType.CONTAINS))
        self.assertEqual(len(some), 2)
        some = list(tree.get([(0, 0), (0, 1)], match=MatchType.CONTAINED))
        self.assertEqual(len(some), 0)
        some = list(tree.get([(0, 0), (0, 1)], match=MatchType.EQUALS))
        self.assertEqual(len(some), 0)
        self.assertEqual(len(tree), 4)
        tree.delete([(0, 0)])
        self.assertEqual(len(tree), 3)
        some = list(tree.get([(0, 0), (0, 1)], match=MatchType.CONTAINS))
        self.assertEqual(len(some), 1)

    def test_known_points(self):
        self.known_points(CLRTree(max_entries=2))
        self.known_points(CLRTree())
        self.known_points(CQRTree(max_entries=2))
        self.known_points(CQRTree())
        self.known_points(CERTree(max_entries=2))
        self.known_points(CERTree())

    def known_boxes(self, tree):
        tree.add([(-0.1, -0.1), (0.1, 0.1)], '0')
        tree.add([(0.9, 0.9), (1.1, 1.1)], '1')
        tree.add([(0, 0), (1, 1)], 'sq')
        tree.add([(2, 2), (3, 3)], 'x')
        some = list(tree.get([(0, 0), (1, 1)], match=MatchType.CONTAINED))
        self.assertEqual(len(some), 1)
        some = list(tree.get([(0, 0), (1, 1)], match=MatchType.CONTAINS))
        self.assertEqual(len(some), 1)
        some = list(tree.get([(0, 0), (2, 1)], match=MatchType.CONTAINED))
        self.assertEqual(len(some), 0)
        some = list(tree.get([(0, 0), (2, 1)], match=MatchType.CONTAINS))
        self.assertEqual(len(some), 1)
        some = list(tree.get([(0, 0), (1, 1)], match=MatchType.OVERLAP))
        self.assertEqual(len(some), 3)

    def test_known_boxes(self):
        self.known_boxes(CLRTree(max_entries=2))
        self.known_boxes(CLRTree())
        self.known_boxes(CQRTree(max_entries=2))
        self.known_boxes(CQRTree())
        self.known_points(CERTree(max_entries=2))
        self.known_points(CERTree())

    def test_delete_points(self):

        for size in 2, 3, 4, 8:

            def new_tree():
                tree = CQRTree(max_entries=size)
                for i in range(4):
                    for j in range(4):
                        tree.add([(i, j)], i+j)
                assert len(tree) == 16
                return tree

            tree = new_tree()
            tree.delete([(1, 2)])
            self.assertEqual(len(tree), 15)

            tree = new_tree()
            tree.delete([(1, 1), (2, 2)])
            self.assertEqual(len(tree), 16)  # default is EQUALS
            tree = new_tree()
            tree.delete([(1, 1), (2, 2)], match=MatchType.CONTAINS)
            self.assertEqual(len(tree), 12)
            tree = new_tree()
            tree.delete([(1, 1), (2, 2)], match=MatchType.CONTAINED)
            self.assertEqual(len(tree), 16)

    def random_box(self, n, size):
        x = uniform(0, size)
        y = uniform(0, size)
        dx = gauss(0, size/sqrt(n))
        dy = gauss(0, size/sqrt(n))
        return [(x, y), (x + dx, y + dy)]

    def gen_random(self, n, size=100):
        for i in range(n):
            yield 1, self.random_box(n, size=size)

    def test_equals(self, ):
        for size in 2, 3, 4, 8:
            tree1 = CQRTree(max_entries=size)
            for i, box in self.gen_random(10):
                tree1.add(box, i)
            tree2 = CQRTree(max_entries=size)
            for k, v in tree1.items():
                tree2.add(k, v)
            self.assertEqual(tree1, tree2)

    def test_underscores(self):

        for size in 2, 3, 4, 8:
            seed(size)
            tree1 = CQRTree(max_entries=size)
            for i, box in self.gen_random(10):
                tree1[box] = i
            tree2 = CQRTree(max_entries=size)
            for k, v in tree1.items():
                tree2.add(k, v)
            self.assertEqual(tree1, tree2)
            if size == 2:
                self.assertEqual(str(tree1), 'Quadratic RTree (10 leaves, 4 height, 1-2 entries)')
            tree3 = CQRTree(tree1.items(), max_entries=size)
            self.assertEqual(tree1, tree3)

        tree = CQRTree()
        tree.add([(1, 1)], '1')
        tree.add([(2, 2)], '2')
        self.assertEqual(len(tree), 2)
        self.assertTrue([(1, 1)] in tree)
        self.assertFalse([(3, 3)] in tree)
        self.assertTrue('1' in list(tree.values()))
        self.assertTrue(((1, 1),) in list(tree.keys()), list(tree.keys()))
        self.assertTrue((((1, 1),), '1') in list(tree.items()))
        del tree[[(1, 1)]]
        self.assertEqual(len(tree), 1)
        self.assertTrue(list(tree[[(2, 2)]]))
        self.assertTrue(list(tree.get([(2, 2)])))
        self.assertTrue(list(tree.get([(2, 2)], value='2')))
        self.assertFalse(list(tree.get([(2, 2)], value='1')))
        self.assertTrue(tree)
        del tree[[(2, 2)]]
        self.assertFalse(tree)

    def best_bug(self, tree):
        for i, (value, box) in enumerate(self.gen_random(100)):
            tree.add(box, value % 10)
            tree.assert_consistent()

    def test_best_bug(self):
        seed(4)  # 1:46 2:17 3:56 4:8 5:10 6:16 7:58 8:8
        self.best_bug(CLRTree(max_entries=2))
        self.best_bug(CQRTree(max_entries=2))
        self.best_bug(CERTree(max_entries=2))

    def stress(self, type, n_children, n_data, check=True):
        seed(1)
        tree = type(max_entries=n_children)
        data = list(self.gen_random(n_data))

        for value, box in data:
            tree.add(box, value)
            if check:
                tree.assert_consistent()

        for i in range(10):

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
                value, box = next(self.gen_random(1))
                data.append((value, box))
                tree.add(box, value)
                if check:
                    tree.assert_consistent()

            for j in range(n_data // 4):
                for match in range(4):
                    list(tree.get(self.random_box(10, 100), match=MatchType(match)))

    def test_stress(self):
        for type in CLRTree, CQRTree, CERTree:
            print('type %s' % type)
            for n_children in 3, 4, 10:
                print('n_children %d' % n_children)
                for n_data in 1, 2, 3, 100:
                    print('n_data %d' % n_data)
                    self.stress(type, n_children, n_data)

    def test_latlon(self):
        tree = LQRTree()
        for lon in -180, 180:
            tree.add([(lon, 0)], str(lon))
        for lon in -180, 180:
            found = list(tree.get([(lon, 0)]))
            self.assertEqual(len(found), 2)
        area = tree._area_of_mbr(tree._mbr_of_points(tree._normalize_points([(-179, -1), (179, 1)])))
        self.assertEqual(area, 4)

        tree = LQRTree()
        tree.add([(180, 0)], None)
        self.assertTrue(((180, 0),) in list(tree.keys()))

    def test_docs(self):
        tree = CQRTree()
        square = ((0,0),(0,1),(1,1),(1,0))
        tree[square] = 'square'
        self.assertEqual(list(tree[square]), ['square'])
        self.assertTrue(square in tree)
        diagonal = ((0,0),(1,1))
        self.assertEqual(list(tree[diagonal]), [])
        self.assertFalse(diagonal in tree)
        self.assertEqual(list(tree.keys()), [((0,0),(0,1),(1,1),(1,0))])
        self.assertEqual(list(tree.values()), ['square'])
        self.assertEqual(list(tree.items()), [(((0,0),(0,1),(1,1),(1,0)), 'square')])
        self.assertEqual(len(tree), 1)
        del tree[square]
        self.assertEqual(len(tree), 0)

        tree = CQRTree(default_match=MatchType.OVERLAP)
        tree[square] = 'square'
        self.assertEqual(list(tree[diagonal]), ['square'])

        tree = CQRTree(default_match=MatchType.OVERLAP)
        tree[square] = 'square'
        self.assertEqual(list(tree.get_items(diagonal)), [(((0,0),(0,1),(1,1),(1,0)), 'square')])

    def test_canary(self):
        tree = CQRTree()
        for i in range(5):
            tree.add([(i, i)], i)
        keys = tree.keys()
        next(keys)
        del tree[[(1, 1)]]
        with self.assertRaisesRegex(RuntimeError, 'mutated'):
            next(keys)

    def measure(self, tree, n_data, n_loops, dim=100):
        seed(1)
        data = list(self.gen_random(n_data, size=dim))
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

    def measure_sizes(self):
        for type in CLRTree, CQRTree, CERTree:
            print()
            for size in 2, 3, 4, 6, 8, 10, 16, 32, 64, 128:
                for subtrees in True, False:
                    t = self.measure(type(max_entries=size, subtrees_flag=subtrees), 1000, 2)
                    print('%s %d %s %s' % (type, size, subtrees, t))
                    if t > 5 and size > 4:
                        print('abort')
                        return

    def test_global(self):

        def test_point(x, y, z):
            t = Global()
            t.add([(x, y)], z)
            l = list(t.get_items([(x, y)]))
            self.assertEqual(len(l), 9)
            for p, q in l:
                self.assertTrue(-0.001 < p[0][0] - x < 0.001)
                self.assertTrue(-0.001 < p[0][1] - y < 0.001)
                self.assertEqual(q, z)

        test_point(0.01, 0.01, 0)
        test_point(179.9, 0.01, 1)
        test_point(-179.9, 0.01, 2)
        test_point(0.01, 89.99, 0)
        test_point(179.9, 89.99, 1)
        test_point(-179.9, 89.99, 2)
        test_point(0.01, -89.99, 0)
        test_point(179.9, -89.99, 1)
        test_point(-179.9, -89.99, 2)

    def run_python(self, tree):
        tree[[(0, 0)]] = 'alice'
        tree[[(10, 10)]] = 'bob'
        tree[[(10, 10)]] = 'charles'

        def show(tree, x, y):
            found = False
            print()
            for entry in tree[[(x, y)]]:
                found = True
                print('%s at (%g,%g)' % (entry, x, y))
            if not found:
                print('nobody at (%g,%g)' % (x, y))

        show(tree, 0, 0)
        show(tree, 5, 5)
        show(tree, 10, 10)

        return tree

    def test_python(self):

        # for other-projects.md
        from ch2.arty import CQRTree, MatchType

        tree = self.run_python(CQRTree())
        self.assertEqual(list(tree[[(0, 0)]]), ['alice'])

        self.run_python(CQRTree(default_match=MatchType.OVERLAP, default_border=3))

