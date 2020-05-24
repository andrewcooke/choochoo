
from logging import getLogger
from tests import LogTestCase

from ch2.data import session
from ch2.data.constraint import constraint, build_source_query

log = getLogger(__name__)


class TestConstraints(LogTestCase):

    def test_example(self):
        # test requires existing database with stats
        s = session('-v5')
        ast = constraint('Active Distance > 10000')[0]
        q = build_source_query(s, ast)
        print(q)
        print(list(q))
