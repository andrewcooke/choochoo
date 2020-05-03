
from logging import getLogger
from tempfile import TemporaryDirectory

from sqlalchemy.sql.functions import count

from ch2.commands.args import bootstrap_dir, m, V, DEV, mm, FORCE
from ch2.commands.constants import constants
from ch2.config.profile.default import default
from ch2.sql.tables.constant import Constant
from tests import LogTestCase

log = getLogger(__name__)


class TestConstant(LogTestCase):

    def test_constant(self):
        with TemporaryDirectory() as f:
            args, sys, db = bootstrap_dir(f, m(V), '5')
            bootstrap_dir(f, m(V), '5', mm(DEV), configurator=default)
            with db.session_context() as s:
                n = s.query(count(Constant.id)).scalar()
                self.assertEqual(n, 14)
            args, sys, db = bootstrap_dir(f, m(V), '5', 'constants', 'set', 'FTHR.%', '154', mm(FORCE))
            constants(args, sys, db)
            with db.session_context() as s:
                n = s.query(count(Constant.id)).scalar()
                self.assertEqual(n, 14)
                # todo - maybe test for value?
                # todo - now that this is defined anyway, change the test?
