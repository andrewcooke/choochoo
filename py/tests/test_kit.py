from subprocess import run
from tempfile import NamedTemporaryFile
from unittest import TestCase

from ch2.commands.activities import activities
from ch2.commands.args import bootstrap_file, m, V, mm, FAST, DEV, D
from ch2.commands.kit import start, change, statistics, finish, show, undo
from ch2.config import default
from ch2.diary.model import TYPE, NAME, ITEMS, COMPONENTS, MODELS, STATISTICS
from ch2.sql import KitModel, KitItem, KitComponent, PipelineType
from ch2.sql.tables.kit import get_name, KitGroup
from ch2.stats.names import ACTIVE_DISTANCE
from ch2.stats.pipeline import run_pipeline


class TestKit(TestCase):

    def test_bikes(self):
        with NamedTemporaryFile() as f:
            args, sys, db = bootstrap_file(f, m(V), '5', configurator=default)
            with db.session_context() as s:
                with self.assertRaises(Exception) as ctx:
                    start(s, 'bike', 'cotic', None, False)
                self.assertTrue('--force' in str(ctx.exception), ctx.exception)
                start(s, 'bike', 'cotic', None, True)
                # run('sqlite3 %s ".dump"' % f.name, shell=True)
                with self.assertRaises(Exception) as ctx:
                    start(s, 'xxxx', 'marin', None, False)
                self.assertTrue('--force' in str(ctx.exception), ctx.exception)
                start(s, 'bike', 'marin', None, False)
                with self.assertRaises(Exception) as ctx:
                    change(s, 'cotic', 'chain', 'sram', '2018-02-01', False, False)
                self.assertTrue('--force' in str(ctx.exception))
                change(s, 'cotic', 'chain', 'sram', None, True, True)
                change(s, 'cotic', 'chain', 'kcm', '2018-01-01', False, False)
                change(s, 'cotic', 'chain', 'sram', '2018-05-01', False, False)
                change(s, 'cotic', 'chain', 'kcm', '2018-07-01', False, False)
                change(s, 'cotic', 'chain', 'sram', '2018-04-01', False, False)
                with self.assertRaises(Exception) as ctx:
                    start(s, 'bike', 'bike', None, True)
                self.assertTrue('bike' in str(ctx.exception), ctx.exception)
                with self.assertRaises(Exception) as ctx:
                    start(s, 'bike', 'sram', None, True)
                self.assertTrue('sram' in str(ctx.exception), ctx.exception)
                start(s, 'bike', 'bowman', None, False)
                change(s, 'bowman', 'chain', 'sram', None, False, True)
                self.assertEqual(len(show(s, 'cotic', None)), 3)
                self.assertEqual(len(statistics(s, 'bike')), 16)
                self.assertEqual(len(statistics(s, 'cotic')), 20)
                self.assertEqual(len(statistics(s, 'chain')), 33)
                self.assertEqual(len(statistics(s, 'sram')), 16)
                finish(s, 'bowman', None, False)
                with self.assertRaises(Exception) as ctx:
                    finish(s, 'bowman', None, False)
                self.assertTrue('retired' in str(ctx.exception), ctx.exception)
                self.assertEqual(len(KitModel.get_all(s, KitItem.get(s, 'cotic'), KitComponent.get(s, 'chain'))), 5)
                undo(s, 'cotic', 'chain', 'sram', None, True)
                self.assertEqual(len(KitModel.get_all(s, KitItem.get(s, 'cotic'), KitComponent.get(s, 'chain'))), 2)
                undo(s, 'cotic', 'chain', 'kcm', None, True)
                self.assertEqual(len(KitModel.get_all(s, KitItem.get(s, 'cotic'), KitComponent.get(s, 'chain'))), 0)
                undo(s, 'bowman', 'chain', 'sram', None, True)
                self.assertFalse(KitComponent.get(s, 'chain', require=False))

    def test_models(self):
        with NamedTemporaryFile() as f:

            args, sys, db = bootstrap_file(f, m(V), '5', configurator=default)
            args, sys, db = bootstrap_file(f, m(V), '5', mm(DEV), 'activities', mm(FAST),
                                           'data/test/source/personal/2018-08-03-rec.fit',
                                           m(D.upper())+'kit=cotic')
            args, sys, db = bootstrap_file(f, m(V), '5', mm(DEV), 'activities', mm(FAST),
                                           'data/test/source/personal/2018-08-27-rec.fit',
                                           m(D.upper())+'kit=cotic')
            activities(args, sys, db)
            run_pipeline(sys, db, PipelineType.STATISTIC, like=['%Activity%'], n_cpu=1)

            with db.session_context() as s:
                start(s, 'bike', 'cotic', '2018-01-01', True)
                start(s, 'bike', 'marin', '2018-01-01', False)
                change(s, 'cotic', 'chain', 'sram', None, True, True)
                change(s, 'cotic', 'chain', 'kcm', '2018-01-01', False, False)
                change(s, 'cotic', 'chain', 'sram', '2018-05-01', False, False)
                change(s, 'cotic', 'chain', 'kcm', '2018-07-01', False, False)
                change(s, 'cotic', 'chain', 'sram', '2018-04-01', False, False)
                start(s, 'bike', 'bowman', '2018-01-01', False)
                change(s, 'bowman', 'chain', 'sram', None, False, True)

            run_pipeline(sys, db, PipelineType.STATISTIC, like=['%Kit%'], n_cpu=1)

            with db.session_context() as s:
                bike = get_name(s, 'bike').to_model(s, depth=3, statistics=True)
                self.assertEqual(bike[TYPE], KitGroup.SIMPLE_NAME)
                self.assertEqual(bike[NAME], 'bike')
                self.assertEqual(len(bike[ITEMS]), 3)
                cotic = [item for item in bike[ITEMS] if item[NAME] == 'cotic'][0]
                self.assertEqual(cotic[TYPE], KitItem.SIMPLE_NAME)
                self.assertEqual(cotic[NAME], 'cotic')
                self.assertEqual(len(cotic[COMPONENTS]), 1)
                chain = cotic[COMPONENTS][0]
                self.assertEqual(chain[TYPE], KitComponent.SIMPLE_NAME)
                self.assertEqual(chain[NAME], 'chain')
                self.assertEqual(len(chain[MODELS]), 6)
                self.assertFalse(STATISTICS in bike)
                print(cotic[STATISTICS])
