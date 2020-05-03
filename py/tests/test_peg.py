
from tests import LogTestCase

from ch2.data.constraint import constraint
from ch2.lib.peg import literal, drop, sequence, choice, pattern


class TestPeg(LogTestCase):

    def test_literal(self):
        self.assertEqual(list(literal('ab')('abc')), [(['ab'], 'c')])

    def test_drop(self):
        self.assertEqual(list(drop(literal('ab'))('abc')), [([], 'c')])

    def test_sequence(self):
        a = literal('a')
        b = literal('b')
        self.assertEqual(list(sequence(a, b)('abc')), [(['a', 'b'], 'c')])

    def test_choice(self):
        a = literal('a')
        b = literal('b')
        self.assertEqual(list(choice(a, b)('abc')), [(['a'], 'bc')])

    def test_pattern(self):
        self.assertEqual(list(pattern(r'(\d+)')('123x')), [(['123'], 'x')])
        self.assertEqual(list(pattern(r'\d+')('123x')), [([], 'x')])
        self.assertEqual(list(pattern(r'\d(\d+)')('123x')), [(['23'], 'x')])

    def test_name(self):
        self.assertEqual(list(constraint('Active Distance > 10')), [('Active Distance', '>', 10.0)])

    def test_term(self):
        self.assertEqual(list(constraint('a = "b" and (c <= 2 or 1.2 > e)')),
                         [(('a', '=', 'b'), 'and', (('c', '<=', 2.0), 'or', ('e', '<', 1.2)))])
        self.assertEqual(list(constraint('a = "b" and c <= 2 or 1.2 > e')),
                         [((('a', '=', 'b'), 'and', ('c', '<=', 2.0)), 'or', ('e', '<', 1.2))])
