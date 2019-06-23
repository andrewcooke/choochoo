
from logging import getLogger
from unittest import TestCase

from ch2.data import session
from ch2.data.constraint import constraint, build_activity_query

log = getLogger(__name__)


class TestConstraints(TestCase):

    def test_example(self):
        # test requires existing database with stats
        s = session('-v5')
        ast = constraint('Active Distance > 10000')[0]
        q = build_activity_query(s, ast)
        print(q)
        print(list(q))

