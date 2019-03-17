
import datetime as dt
from tempfile import NamedTemporaryFile
from unittest import TestCase

from sqlalchemy.sql.functions import count

from ch2.commands.args import bootstrap_file, m, V, mm, DEV
from ch2.config import default, getLogger
from ch2.squeal.tables.timestamp import Timestamp

log = getLogger(__name__)


class TestTimestamp(TestCase):

    def test_set(self):
        with NamedTemporaryFile() as f:
            args, db = bootstrap_file(f, m(V), '5')
            bootstrap_file(f, m(V), '5', mm(DEV), configurator=default)
            with db.session_context() as s:
                n = s.query(count(Timestamp.id)).scalar()
                self.assertEqual(n, 0)
                Timestamp.set(log, s, TestTimestamp, None, 1)
                n = s.query(count(Timestamp.id)).scalar()
                self.assertEqual(n, 1)
                t = s.query(Timestamp).filter(Timestamp.owner == TestTimestamp).one()
                self.assertAlmostEqual(t.time.timestamp(), dt.datetime.now().timestamp(), 1)

    def test_context(self):
        with NamedTemporaryFile() as f:
            args, db = bootstrap_file(f, m(V), '5')
            bootstrap_file(f, m(V), '5', mm(DEV), configurator=default)
            with db.session_context() as s:
                with Timestamp(owner=TestTimestamp).on_success(log, s):
                    n = s.query(count(Timestamp.id)).scalar()
                    self.assertEqual(n, 0)
                n = s.query(count(Timestamp.id)).scalar()
                self.assertEqual(n, 1)

    def test_context_error(self):
        with NamedTemporaryFile() as f:
            args, db = bootstrap_file(f, m(V), '5')
            bootstrap_file(f, m(V), '5', mm(DEV), configurator=default)
            with db.session_context() as s:
                try:
                    with Timestamp(owner=TestTimestamp).on_success(log, s):
                        n = s.query(count(Timestamp.id)).scalar()
                        self.assertEqual(n, 0)
                        raise Exception('foo')
                except Exception as e:
                    self.assertEqual(str(e), 'foo')  # for some weird reason assertRaisesRegex was not working
                n = s.query(count(Timestamp.id)).scalar()
                self.assertEqual(n, 0)
