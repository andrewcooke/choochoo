
from tempfile import NamedTemporaryFile
from unittest import TestCase

from ch2.commands.args import bootstrap_file, m, V
from ch2.commands.kit import new, add, statistics, retire, show
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
                # run('sqlite3 %s ".dump"' % f.name, shell=True)
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
                new(s, 'bike', 'bowman', None, False)
                add(s, 'bowman', 'chain', 'sram', None, False)
                self.assertEquals(len(show(s, 'cotic', None)), 3)
                self.assertEqual(len(statistics(s, 'bike')), 16)
                self.assertEqual(len(statistics(s, 'cotic')), 20)
                self.assertEqual(len(statistics(s, 'chain')), 33)
                self.assertEqual(len(statistics(s, 'sram')), 16)
                retire(s, 'bowman', None, False)
                with self.assertRaises(Exception) as ctx:
                    retire(s, 'bowman', None, False)
                self.assertTrue('retired' in str(ctx.exception), ctx.exception)
                retire(s, 'sram')