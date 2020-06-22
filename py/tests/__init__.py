
from unittest import TestCase

from ch2.lib.log import make_log


class LogTestCase(TestCase):

    def setUp(self):
        make_log('/tmp/ch2-test.log', verbosity=5)
