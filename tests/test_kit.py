
from tempfile import NamedTemporaryFile
from unittest import TestCase

from ch2.commands.args import bootstrap_file, m, V
from ch2.commands.kit import new, add
from ch2.config import default


class TestKit(TestCase):

    def test_bikes(self):
        with NamedTemporaryFile() as f:
            args, db = bootstrap_file(f, m(V), '5', configurator=default)
            with db.session_context() as s:
                with self.assertRaises(Exception) as ctx:
                    new(s, 'bike', 'cotic', None, False)
                self.assertTrue('--force' in str(ctx.exception), ctx.exception)
                new(s, 'bike', 'cotic', None, True)
                with self.assertRaises(Exception) as ctx:
                    new(s, 'xxxx', 'marin', None, False)
                self.assertTrue('--force' in str(ctx.exception), ctx.exception)
                new(s, 'bike', 'marin', None, False)
                with self.assertRaises(Exception) as ctx:
                    add(s, 'cotic', 'chain', 'sram', '2018-02-01', False)
                self.assertTrue('--force' in str(ctx.exception))
                add(s, 'cotic', 'chain', 'sram', '2018-02-01', True)
                add(s, 'cotic', 'chain', 'kcm', '2018-01-01', False)
                add(s, 'cotic', 'chain', 'sram', '2018-05-01', False)
                add(s, 'cotic', 'chain', 'kcm', '2018-07-01', False)
                add(s, 'cotic', 'chain', 'sram', '2018-04-01', False)
                with self.assertRaises(Exception) as ctx:
                    new(s, 'bike', 'bike', None, True)
                self.assertTrue('bike' in str(ctx.exception), ctx.exception)
                with self.assertRaises(Exception) as ctx:
                    new(s, 'bike', 'sram', None, True)
                self.assertTrue('sram' in str(ctx.exception), ctx.exception)

