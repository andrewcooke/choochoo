
from logging import getLogger
from tempfile import NamedTemporaryFile
from unittest import TestCase

from sqlalchemy.sql.functions import count

from ch2.commands.args import bootstrap_file, m, V, DEV, mm
from ch2.commands.constants import constants
from ch2.config.default import default
from ch2.squeal.tables.constant import Constant

log = getLogger(__name__)


class TestConstant(TestCase):

    def test_constant(self):
        with NamedTemporaryFile() as f:
            args, db = bootstrap_file(f, m(V), '5')
            bootstrap_file(f, m(V), '5', mm(DEV), configurator=default)
            with db.session_context() as s:
                n = s.query(count(Constant.id)).scalar()
                self.assertEqual(n, 10)
            args, db = bootstrap_file(f, m(V), '5', 'constants', '--set', 'FTHR.%', '154')
            constants(args, db)
            with db.session_context() as s:
                n = s.query(count(Constant.id)).scalar()
                self.assertEqual(n, 10)
                # todo - maybe test for value?
