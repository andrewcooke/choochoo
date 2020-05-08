
from ch2.names import Names, titles_for_names
from tests import LogTestCase


class TestNames(LogTestCase):

    def test_names(self):
        self.assertEqual(Names.HEART_RATE, 'heart_rate')
        self.assertEqual(Names.DELTA_AIR_SPEED_2, 'd_air_speed_2')
        self.assertEqual(Names._avg('foo'), 'avg_foo')

    def test_titles_for_names(self):
        self.assertEqual(list(titles_for_names('A%C', ['abc', 'ABC', 'aBc'])), ['AbC', 'ABC'])
