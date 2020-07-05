from logging import getLogger

from ch2.names import SPACE, simple_name
from tests import LogTestCase

log = getLogger(__name__)


class TestName(LogTestCase):

    def test_tokenzie(self):
        self.assertEqual(simple_name('ABC 123 *^%'), 'abc-123-%')  # support for like
        self.assertEqual(simple_name('****'), SPACE)
        self.assertEqual(simple_name('123'), '-123')
        self.assertEqual(simple_name('Fitness 7d'), 'fitness-7d')
