
from unittest import TestCase

from ch2.lib.data import AttrDict


class TestData(TestCase):

    def test_attr(self):
        d = AttrDict()
        d['foo'] = 'bar'
        self.assertTrue('foo' in d)
        self.assertEqual(d.foo, 'bar')

