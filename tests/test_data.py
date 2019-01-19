
from unittest import TestCase

from ch2.lib.data import MutableAttr


class TestData(TestCase):

    def test_attr(self):
        d = MutableAttr()
        d['foo'] = 'bar'
        self.assertTrue('foo' in d)
        self.assertEqual(d.foo, 'bar')

