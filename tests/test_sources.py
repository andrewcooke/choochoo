
from tempfile import NamedTemporaryFile

from ch2.args import DATABASE, mm, m, V, NamespaceWithVariables, parser
from ch2.config.database import config
from ch2.config.personal import acooke
from ch2.log import make_log
from ch2.squeal.database import Database


# the idea here is to test the new database schema with sources etc
# so we configure a database then load some data, calculate some stats, and see if everything works as expected.


def test_sources():

    with NamedTemporaryFile() as f:

        args = [mm(DATABASE), f.name, m(V), '5']
        c = config(*args)
        acooke(c)

        # todo - this should be simpler
        p = parser()
        a = NamespaceWithVariables(p.parse_args(args))
        log = make_log(a)
        db = Database(a, log)
