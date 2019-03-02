
from tempfile import NamedTemporaryFile
from unittest import TestCase

from sqlalchemy.sql.functions import count

from ch2.command.args import bootstrap_file, m, V, DEV, mm
from ch2.command.constants import constants
from ch2.config.default import default
from ch2.squeal.tables.constant import Constant


class TestConstant(TestCase):

    def test_constant(self):
        with NamedTemporaryFile() as f:
            args, log, db = bootstrap_file(f, m(V), '5')
            bootstrap_file(f, m(V), '5', mm(DEV), configurator=default)
            with db.session_context() as s:
                n = s.query(count(Constant.id)).scalar()
                self.assertEqual(n, 9)
            args, log, db = bootstrap_file(f, m(V), '5', 'constants', '--set', 'FTHR.%', '154')
            constants(args, log, db)
            with db.session_context() as s:
                n = s.query(count(Constant.id)).scalar()
                self.assertEqual(n, 9)
                # todo - maybe test for value?
