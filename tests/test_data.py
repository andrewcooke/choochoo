
from ch2.lib.data import AttrDict


def test_attr():
    d = AttrDict()
    d['foo'] = 'bar'
    assert 'foo' in d
    assert d.foo == 'bar'
