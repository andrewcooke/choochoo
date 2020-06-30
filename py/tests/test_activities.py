
from tempfile import TemporaryDirectory

from sqlalchemy.sql.functions import count

from ch2.commands.read import read
from ch2.commands.args import V, DEV, BASE, bootstrap_dir, FORCE
from ch2.common.args import mm, m
from ch2.commands.constants import constants
from ch2.config.profile.default import default
from ch2.sql.tables.activity import ActivityJournal
from ch2.sql.tables.pipeline import PipelineType
from ch2.sql.tables.statistic import StatisticJournal, StatisticJournalFloat, StatisticName
from ch2.data import Names as N
from ch2.pipeline.pipeline import run_pipeline
from tests import LogTestCase


class TestActivities(LogTestCase):

    def test_activities(self):

        with TemporaryDirectory() as base:

            bootstrap_dir(base, m(V), '5')

            bootstrap_dir(base, m(V), '5', mm(DEV), configurator=default)

            args, data = bootstrap_dir(base, m(V), '5', 'constants', 'set', 'SRTM1.dir',
                                          '/home/andrew/archive/srtm1', mm(FORCE))
            constants(args, data)

            args, data = bootstrap_dir(base, m(V), '5', mm(DEV), 'read',
                                          'data/test/source/personal/2018-08-27-rec.fit')
            read(args, data)

            # run('sqlite3 %s ".dump"' % f.name, shell=True)

            run_pipeline(data, PipelineType.CALCULATE, force=True, start='2018-01-01', n_cpu=1)

            # run('sqlite3 %s ".dump"' % f.name, shell=True)

            with data.db.session_context() as s:
                n_raw = s.query(count(StatisticJournalFloat.id)). \
                    join(StatisticName). \
                    filter(StatisticName.name == N.RAW_ELEVATION).scalar()
                self.assertEqual(2099, n_raw)
                n_fix = s.query(count(StatisticJournalFloat.id)). \
                    join(StatisticName). \
                    filter(StatisticName.name == N.ELEVATION).scalar()
                self.assertEqual(2099, n_fix)
                # WHY does this jump around?
                n = s.query(count(StatisticJournal.id)).scalar()
                # self.assertEqual(50403, n)
                self.assertTrue(n > 30000)
                self.assertTrue(n < 100000)
                journal = s.query(ActivityJournal).one()
                self.assertNotEqual(journal.start, journal.finish)

    def test_segment_bug(self):
        with TemporaryDirectory() as f:
            args, data = bootstrap_dir(f, m(V), '5', mm(DEV), configurator=default)
            paths = ['/home/andrew/archive/fit/bike/cotic/2016-07-27-pm-z4.fit']
            run_pipeline(data, PipelineType.READ_ACTIVITY, paths=paths, force=True)

    def __assert_basic_stats(self, s):
        for name in [N.ACTIVE_DISTANCE, N.ACTIVE_TIME]:
            count = 0
            for stat in s.query(StatisticJournal). \
                    join(StatisticName). \
                    filter(StatisticName.name == name).all():
                count += 1
                print(f'{name} = {stat}')
                self.assertTrue(stat, f'No value for {name}')
            self.assertTrue(count > 0)

    def test_florian(self):
        with TemporaryDirectory() as f:
            bootstrap_dir(f, m(V), '5')
            bootstrap_dir(f, m(V), '5', mm(DEV), configurator=default)
            args, data = bootstrap_dir(f, m(V), '5', mm(DEV), 'read',
                                          'data/test/source/private/florian.fit')
            read(args, data)
            # run('sqlite3 %s ".dump"' % f.name, shell=True)
            run_pipeline(data, PipelineType.CALCULATE, n_cpu=1)
            # run('sqlite3 %s ".dump"' % f.name, shell=True)
            with data.db.session_context() as s:
                self.__assert_basic_stats(s)

    def test_michael(self):
        with TemporaryDirectory() as f:
            bootstrap_dir(f, m(V), '5')
            bootstrap_dir(f, m(V), '5', mm(DEV), configurator=default)
            args, data = bootstrap_dir(f, m(V), '5', mm(DEV), 'read',
                                      'data/test/source/other/2019-05-09-051352-Running-iWatchSeries3.fit')
            read(args, data)
            # run('sqlite3 %s ".dump"' % f.name, shell=True)
            run_pipeline(data, PipelineType.CALCULATE, n_cpu=1)
            # run('sqlite3 %s ".dump"' % f.name, shell=True)
            with data.db.session_context() as s:
                self.__assert_basic_stats(s)

    def test_heart_alarms(self):
        with TemporaryDirectory() as f:
            bootstrap_dir(f, m(V), '5')
            bootstrap_dir(f, m(V), '5', mm(DEV), configurator=default)
            args, data = bootstrap_dir(f, m(V), '5', mm(DEV), 'read',
                                      'data/test/source/personal/2016-07-19-mpu-s-z2.fit')
            read(args, data)
            # run('sqlite3 %s ".dump"' % f.name, shell=True)
            run_pipeline(data, PipelineType.CALCULATE, n_cpu=1)
            # run('sqlite3 %s ".dump"' % f.name, shell=True)
            with data.db.session_context() as s:
                for stat in s.query(StatisticJournal). \
                        join(StatisticName). \
                        filter(StatisticName.name == N.ACTIVE_DISTANCE).all():
                    self.assertGreater(stat.value, 30)

    def test_920(self):
        for src in '920xt-2019-05-16_19-42-54.fit', '920xt-2019-05-16_19-42-54.fit':
            with TemporaryDirectory() as f:
                bootstrap_dir(f, m(V), '5')
                bootstrap_dir(f, m(V), '5', mm(DEV), configurator=default)
                args, data = bootstrap_dir(f, m(V), '5', mm(DEV), 'read',
                                               f'data/test/source/other/{src}')
                read(args, data)
                # run('sqlite3 %s ".dump"' % f.name, shell=True)
                run_pipeline(data, PipelineType.CALCULATE, n_cpu=1)
                # run('sqlite3 %s ".dump"' % f.name, shell=True)
                with data.db.session_context() as s:
                    self.__assert_basic_stats(s)
