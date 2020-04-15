from io import StringIO
from tempfile import TemporaryDirectory

from ch2.commands.activities import activities
from ch2.commands.args import bootstrap_dir, m, V, mm, DEV, D, BASE
from ch2.commands.kit import start, change, finish, show, undo, statistics
from ch2.config import default
from ch2.diary.model import TYPE
from ch2.lib import now, local_date_to_time
from ch2.sql import KitModel, KitItem, KitComponent, PipelineType
from ch2.sql.tables.kit import get_name, KitGroup, NAME, ITEMS, COMPONENTS, MODELS, STATISTICS, INDIVIDUAL
from ch2.stats.pipeline import run_pipeline
from tests import LogTestCase


def days(date):
    return (now() - local_date_to_time(date)).days


class TestKit(LogTestCase):

    def test_bikes(self):
        with TemporaryDirectory() as f:
            args, sys, db = bootstrap_dir(f, m(V), '5', configurator=default)
            with db.session_context() as s:
                with self.assertRaises(Exception) as ctx:
                    start(s, 'bike', 'cotic', '2020-03-24', False)
                self.assertTrue('--force' in str(ctx.exception), ctx.exception)
                start(s, 'bike', 'cotic', '2020-03-24', True)
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
                self.assert_command('''item: cotic  2020-03-24 - 
`-component: chain
  +-model: sram  2020-03-24 - 
  +-model: kcm  2018-01-01 - 2018-04-01
  +-model: sram  2018-05-01 - 2018-07-01
  +-model: kcm  2018-07-01 - 2020-03-24
  `-model: sram  2018-04-01 - 2018-05-01
''', show, s, 'cotic', None)
                self.assert_command(f'''group: bike
+-item: cotic
| +-Age
| | +-n: 1
| | `-sum: {days('2020-03-24')}
| `-component: chain
|   +-model: sram
|   | `-Age
|   |   +-n: 1
|   |   `-sum: {days('2020-03-24')}
|   +-model: kcm
|   | `-Age
|   |   +-n: 1
|   |   `-sum: 90
|   +-model: sram
|   | `-Age
|   |   +-n: 1
|   |   `-sum: 61
|   +-model: kcm
|   | `-Age
|   |   +-n: 1
|   |   `-sum: 631
|   `-model: sram
|     `-Age
|       +-n: 1
|       `-sum: 30
+-item: marin
| `-Age
|   +-n: 1
|   `-sum: 0
`-item: bowman
  +-Age
  | +-n: 1
  | `-sum: 0
  `-component: chain
    `-model: sram
      `-Age
        +-n: 1
        `-sum: 0
''', statistics, s, 'bike')
                self.assert_command(f'''item: cotic
+-Age
| +-n: 1
| `-sum: {days('2020-03-24')}
`-component: chain
  +-model: sram
  | `-Age
  |   +-n: 1
  |   `-sum: {days('2020-03-24')}
  +-model: kcm
  | `-Age
  |   +-n: 1
  |   `-sum: 90
  +-model: sram
  | `-Age
  |   +-n: 1
  |   `-sum: 61
  +-model: kcm
  | `-Age
  |   +-n: 1
  |   `-sum: 631
  `-model: sram
    `-Age
      +-n: 1
      `-sum: 30
''', statistics, s, 'cotic')
                self.assert_command(f'''component: chain
+-model: sram
| `-Age
|   +-n: 1
|   `-sum: {days('2020-03-24')}
+-model: kcm
| `-Age
|   +-n: 1
|   `-sum: 90
+-model: sram
| `-Age
|   +-n: 1
|   `-sum: 61
+-model: kcm
| `-Age
|   +-n: 1
|   `-sum: 631
+-model: sram
| `-Age
|   +-n: 1
|   `-sum: 30
`-model: sram
  `-Age
    +-n: 1
    `-sum: 0
''', statistics, s, 'chain')
                self.assert_command(f'''model: sram
`-Age
  +-n: 1
  `-sum: {days('2020-03-24')}
''', statistics, s, 'sram')
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

    def assert_command(self, text, cmd, *args):
        args = list(args)
        output = StringIO()
        cmd(*args, output=output)
        self.assertEqual(output.getvalue(), text)

    def test_models(self):
        with TemporaryDirectory() as f:

            args, sys, db = bootstrap_dir(f, m(V), '5', configurator=default)
            args, sys, db = bootstrap_dir(f, m(V), '5', mm(DEV), 'activities',
                                           'data/test/source/personal/2018-08-03-rec.fit',
                                           m(D.upper())+'kit=cotic')
            activities(args, sys, db)
            args, sys, db = bootstrap_dir(f, m(V), '5', mm(DEV), 'activities',
                                           'data/test/source/personal/2018-08-27-rec.fit',
                                           m(D.upper())+'kit=cotic')
            activities(args, sys, db)
            run_pipeline(sys, db, args[BASE], PipelineType.STATISTIC, like=['%Activity%'], n_cpu=1)

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

            run_pipeline(sys, db, args[BASE], PipelineType.STATISTIC, like=['%Kit%'], n_cpu=1)

            with db.session_context() as s:
                bike = get_name(s, 'bike').to_model(s, depth=3, statistics=INDIVIDUAL, own_models=False)
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
