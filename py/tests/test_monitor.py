from logging import getLogger
from subprocess import run
from tempfile import TemporaryDirectory

import sqlalchemy.sql.functions as func

from ch2 import BASE
from ch2.commands.args import V, DEV, MONITOR, base_system_path, bootstrap_db, READ
from ch2.commands.read import read
from ch2.common.args import mm, m
from ch2.common.date import to_time, local_date_to_time
from ch2.config.profile.default import default
from ch2.data import Names as N
from ch2.pipeline.calculate.monitor import MonitorCalculator
from ch2.pipeline.pipeline import run_pipeline
from ch2.sql.tables.monitor import MonitorJournal
from ch2.sql.tables.pipeline import PipelineType
from ch2.sql.tables.statistic import StatisticJournal, StatisticName
from tests import LogTestCase, random_test_user

log = getLogger(__name__)


class TestMonitor(LogTestCase):

    def test_monitor(self):
        user = random_test_user()
        bootstrap_db(user, m(V), '5')
        with TemporaryDirectory() as f:
            bootstrap_db(user, mm(BASE), f, m(V), '5', mm(DEV), configurator=default)
            config = bootstrap_db(user, mm(BASE), f, m(V), '5', mm(DEV),
                                      READ, 'data/test/source/personal/25822184777.fit')
            read(config)
            run_pipeline(config, PipelineType.CALCULATE, force=True, start='2018-01-01', finish='2018-12-01', n_cpu=1)
            with config.db.session_context() as s:
                n = s.query(func.count(StatisticJournal.id)).scalar()
                self.assertEqual(164, n)
                mjournal = s.query(MonitorJournal).one()
                self.assertNotEqual(mjournal.start, mjournal.finish)

    def test_values(self):
        user = random_test_user()
        with TemporaryDirectory() as f:
            bootstrap_db(user, m(V), '5')
            bootstrap_db(user, mm(BASE), f, m(V), '5', mm(DEV), configurator=default)
            for file in ('24696157869', '24696160481', '24696163486'):
                config = bootstrap_db(user, mm(BASE), f, m(V), '5', mm(DEV),
                                           'read', mm(MONITOR),
                                           'data/test/source/personal/andrew@acooke.org_%s.fit' % file)
                read(config)
            run_pipeline(config, PipelineType.CALCULATE, force=True, like=('%Monitor%',), start='2018-01-01', n_cpu=1)
            with config.db.session_context() as s:
                mjournals = s.query(MonitorJournal).order_by(MonitorJournal.start).all()
                assert mjournals[2].start == to_time('2018-09-06 15:06:00'), mjournals[2].start
                # steps
                summary = s.query(StatisticJournal).join(StatisticName). \
                    filter(StatisticJournal.time >= local_date_to_time('2018-09-06'),
                           StatisticJournal.time < local_date_to_time('2018-09-07'),
                           StatisticName.owner == MonitorCalculator,
                           StatisticName.name == N.DAILY_STEPS).one()
                # connect has 12757 for this date,
                self.assertEqual(summary.value, 12757)

    FILES = ('25505915679', '25519562859', '25519565531', '25532154264', '25539076032', '25542112328')

    def generic_bug(self, files, join=False):
        user = random_test_user()
        with TemporaryDirectory() as f:
            config = bootstrap_db(user, m(V), '5')
            bootstrap_db(user, mm(BASE), f, m(V), '5', mm(DEV), configurator=default)
            if join:
                files = ['data/test/source/personal/andrew@acooke.org_%s.fit' % file for file in files]
                config = bootstrap_db(user, mm(BASE), f, mm(DEV), 'read', *files)
                read(config)
            else:
                for file in files:
                    config = bootstrap_db(user, mm(BASE), f, mm(DEV), 'read',
                                               'data/test/source/personal/andrew@acooke.org_%s.fit' % file)
                    read(config)
            # run('sqlite3 %s ".dump"' % f.name, shell=True)
            with config.db.session_context() as s:
                # steps
                summary = s.query(StatisticJournal).join(StatisticName). \
                    filter(StatisticJournal.time >= local_date_to_time('2018-10-07'),
                           StatisticJournal.time < local_date_to_time('2018-10-08'),
                           StatisticName.owner == MonitorCalculator,
                           StatisticName.name == N.DAILY_STEPS).one()
                # connect has 3031 for this date.
                self.assertEqual(summary.value, 3031)

    def test_bug(self):
        self.generic_bug(sorted(self.FILES))

    def test_bug_reversed(self):
        self.generic_bug(sorted(self.FILES, reverse=True))

    def test_bug_join(self):
        self.generic_bug(sorted(self.FILES), join=True)

    def test_bug_reversed_join(self):
        self.generic_bug(sorted(self.FILES, reverse=True), join=True)

    # issue 6
    def test_empty_data(self):
        user = random_test_user()
        with TemporaryDirectory() as f:
            bootstrap_db(user, mm(BASE), f, m(V), '5')
            bootstrap_db(user, mm(BASE), f, m(V), '5', mm(DEV), configurator=default)
            config = bootstrap_db(user, mm(BASE), f, m(V), '5', mm(DEV),
                                      'read', 'data/test/source/other/37140810636.fit')
            read(config)
            # run('sqlite3 %s ".dump"' % f.name, shell=True)
            run_pipeline(config, PipelineType.CALCULATE, n_cpu=1)
            # run('sqlite3 %s ".dump"' % f.name, shell=True)
            with config.db.session_context() as s:
                n = s.query(func.count(StatisticJournal.id)).scalar()
                self.assertEqual(n, 44)
                mjournal = s.query(MonitorJournal).one()
                self.assertNotEqual(mjournal.start, mjournal.finish)
