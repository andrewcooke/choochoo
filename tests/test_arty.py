
from ch2.arty.tree import CLRTree, MatchType


def test_cl_known_points():

    tree = CLRTree(None, 2)
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

    tree = CLRTree(None, 2)
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

