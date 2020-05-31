
from logging import getLogger
from subprocess import run
from tempfile import TemporaryDirectory

import sqlalchemy.sql.functions as func

from ch2 import monitor
from ch2.commands.args import bootstrap_dir, m, V, DEV, mm, BASE
from ch2.config.profile.default import default
from ch2.lib.date import to_time, local_date_to_time
from ch2.sql.tables.monitor import MonitorJournal
from ch2.sql.tables.pipeline import PipelineType
from ch2.sql.tables.statistic import StatisticJournal, StatisticName
from ch2.pipeline.calculate.monitor import MonitorCalculator
from ch2.names import REST_HR, DAILY_STEPS
from ch2.pipeline.pipeline import run_pipeline
from tests import LogTestCase

log = getLogger(__name__)


class TestMonitor(LogTestCase):

    def test_monitor(self):
        with TemporaryDirectory() as f:
            args, sys, db = bootstrap_dir(f, m(V), '5')
            bootstrap_dir(f, m(V), '5', mm(DEV), configurator=default)
            args, sys, db = bootstrap_dir(f, m(V), '5', mm(DEV),
                                      'monitor', 'data/test/source/personal/25822184777.fit')
            monitor(args, sys, db)
            # run('sqlite3 %s ".dump"' % f.name, shell=True)
            run_pipeline(sys, db, args[BASE], PipelineType.CALCULATE, force=True, start='2018-01-01', n_cpu=1)
            # run('sqlite3 %s ".dump"' % f.name, shell=True)
            with db.session_context() as s:
                n = s.query(func.count(StatisticJournal.id)).scalar()
                self.assertEqual(n, 121)
                mjournal = s.query(MonitorJournal).one()
                self.assertNotEqual(mjournal.start, mjournal.finish)

    def test_values(self):
        with TemporaryDirectory() as f:
            bootstrap_dir(f, m(V), '5')
            bootstrap_dir(f, m(V), '5', mm(DEV), configurator=default)
            for file in ('24696157869', '24696160481', '24696163486'):
                args, sys, db = bootstrap_dir(f, m(V), '5', mm(DEV),
                                          'monitor', 'data/test/source/personal/andrew@acooke.org_%s.fit' % file)
                monitor(args, sys, db)
            # run('sqlite3 %s ".dump"' % f.name, shell=True)
            run_pipeline(sys, db, args[BASE], PipelineType.CALCULATE, force=True, start='2018-01-01', n_cpu=1)
            with db.session_context() as s:
                mjournals = s.query(MonitorJournal).order_by(MonitorJournal.start).all()
                assert mjournals[2].start == to_time('2018-09-06 15:06:00'), mjournals[2].start
                # steps
                summary = s.query(StatisticJournal).join(StatisticName). \
                    filter(StatisticJournal.time >= local_date_to_time('2018-09-06'),
                           StatisticJournal.time < local_date_to_time('2018-09-07'),
                           StatisticName.owner == MonitorCalculator,
                           StatisticName.name == DAILY_STEPS).one()
                # connect has 12757 for this date,
                self.assertEqual(summary.value, 12757)
                path = args.system_path(subdir='data', file='activity.db')
                run('sqlite3 %s "select * from statistic_journal as j, statistic_journal_integer as i, '
                    'statistic_name as n where j.id = i.id and j.statistic_name_id = n.id and '
                    'n.name = \'Steps\' order by j.time"' % path, shell=True)
                run('sqlite3 %s "select * from statistic_journal as j, statistic_journal_integer as i, '
                    'statistic_name as n where j.id = i.id and j.statistic_name_id = n.id and '
                    'n.name = \'Cumulative Steps\' order by j.time"' % path, shell=True)
                # heart rate
                summary = s.query(StatisticJournal).join(StatisticName). \
                    filter(StatisticJournal.time >= local_date_to_time('2018-09-06'),
                           StatisticJournal.time < local_date_to_time('2018-09-07'),
                           StatisticName.owner == MonitorCalculator,
                           StatisticName.name == REST_HR).one()
                self.assertEqual(summary.value, 45)

    FILES = ('25505915679', '25519562859', '25519565531', '25532154264', '25539076032', '25542112328')

    def generic_bug(self, files):
        with TemporaryDirectory() as f:
            args, sys, db = bootstrap_dir(f, m(V), '5')
            bootstrap_dir(f, m(V), '5', mm(DEV), configurator=default)
            for file in files:
                args, sys, db = bootstrap_dir(f, m(V), '5', mm(DEV), 'monitor',
                                               'data/test/source/personal/andrew@acooke.org_%s.fit' % file)
                monitor(args, sys, db)
            # run('sqlite3 %s ".dump"' % f.name, shell=True)
            run_pipeline(sys, db, args[BASE], PipelineType.CALCULATE, force=True, start='2018-01-01', n_cpu=1)
            # run('sqlite3 %s ".dump"' % f.name, shell=True)
            with db.session_context() as s:
                # steps
                summary = s.query(StatisticJournal).join(StatisticName). \
                    filter(StatisticJournal.time >= local_date_to_time('2018-10-07'),
                           StatisticJournal.time < local_date_to_time('2018-10-08'),
                           StatisticName.owner == MonitorCalculator,
                           StatisticName.name == DAILY_STEPS).one()
                # connect has 3031 for this date.
                self.assertEqual(summary.value, 3031)

    def test_bug(self):
        self.generic_bug(sorted(self.FILES))

    def test_bug_reversed(self):
        self.generic_bug(sorted(self.FILES, reverse=True))

    # issue 6
    def test_empty_data(self):
        with TemporaryDirectory() as f:
            args, sys, db = bootstrap_dir(f, m(V), '5')
            bootstrap_dir(f, m(V), '5', mm(DEV), configurator=default)
            args, sys, db = bootstrap_dir(f, m(V), '5', mm(DEV),
                                      'monitor', 'data/test/source/other/37140810636.fit')
            monitor(args, sys, db)
            # run('sqlite3 %s ".dump"' % f.name, shell=True)
            run_pipeline(sys, db, args[BASE], PipelineType.CALCULATE, n_cpu=1)
            # run('sqlite3 %s ".dump"' % f.name, shell=True)
            with db.session_context() as s:
                n = s.query(func.count(StatisticJournal.id)).scalar()
                self.assertEqual(n, 28)
                mjournal = s.query(MonitorJournal).one()
                self.assertNotEqual(mjournal.start, mjournal.finish)
