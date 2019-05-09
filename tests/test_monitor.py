
from logging import getLogger
from subprocess import run
from tempfile import NamedTemporaryFile
from unittest import TestCase

import sqlalchemy.sql.functions as func

from ch2 import monitor
from ch2.commands.args import bootstrap_file, m, V, DEV, mm, FAST
from ch2.config.default import default
from ch2.lib.date import to_time, local_date_to_time
from ch2.squeal.tables.monitor import MonitorJournal
from ch2.squeal.tables.pipeline import PipelineType
from ch2.squeal.tables.statistic import StatisticJournal, StatisticName
from ch2.stoats.calculate.monitor import MonitorCalculator
from ch2.stoats.names import REST_HR, DAILY_STEPS
from ch2.stoats.pipeline import run_pipeline

log = getLogger(__name__)


class TestMonitor(TestCase):

    def test_monitor(self):
        with NamedTemporaryFile() as f:
            args, db = bootstrap_file(f, m(V), '5')
            bootstrap_file(f, m(V), '5', mm(DEV), configurator=default)
            args, db = bootstrap_file(f, m(V), '5', mm(DEV),
                                      'monitor', mm(FAST), 'data/test/source/personal/25822184777.fit')
            monitor(args, db)
            # run('sqlite3 %s ".dump"' % f.name, shell=True)
            run_pipeline(db, PipelineType.STATISTIC, force=True, start='2018-01-01')
            # run('sqlite3 %s ".dump"' % f.name, shell=True)
            with db.session_context() as s:
                n = s.query(func.count(StatisticJournal.id)).scalar()
                # self.assertEqual(n, 111)
                self.assertEqual(n, 108)  # why?
                mjournal = s.query(MonitorJournal).one()
                self.assertNotEqual(mjournal.start, mjournal.finish)

    def test_values(self):
        with NamedTemporaryFile() as f:
            bootstrap_file(f, m(V), '5')
            bootstrap_file(f, m(V), '5', mm(DEV), configurator=default)
            for file in ('24696157869', '24696160481', '24696163486'):
                args, db = bootstrap_file(f, m(V), '5', mm(DEV),
                                          'monitor', mm(FAST),
                                          'data/test/source/personal/andrew@acooke.org_%s.fit' % file)
                monitor(args, db)
            # run('sqlite3 %s ".dump"' % f.name, shell=True)
            run_pipeline(db, PipelineType.STATISTIC, force=True, start='2018-01-01', n_cpu=1)
            run('sqlite3 %s ".dump"' % f.name, shell=True)
            with db.session_context() as s:
                mjournals = s.query(MonitorJournal).order_by(MonitorJournal.start).all()
                assert mjournals[2].start == to_time('2018-09-06 15:06:00'), mjournals[2].start
                print(mjournals[2].fit_file)
                # steps
                summary = s.query(StatisticJournal).join(StatisticName). \
                    filter(StatisticJournal.time >= local_date_to_time('2018-09-06'),
                           StatisticJournal.time < local_date_to_time('2018-09-07'),
                           StatisticName.owner == MonitorCalculator,
                           StatisticName.name == DAILY_STEPS).one()
                # connect has 12757 for this date,
                self.assertEqual(summary.value, 12757)
                # heart rate
                summary = s.query(StatisticJournal).join(StatisticName). \
                    filter(StatisticJournal.time >= local_date_to_time('2018-09-06'),
                           StatisticJournal.time < local_date_to_time('2018-09-07'),
                           StatisticName.owner == MonitorCalculator,
                           StatisticName.name == REST_HR).one()
                self.assertEqual(summary.value, 45)

    FILES = ('25505915679', '25519562859', '25519565531', '25532154264', '25539076032', '25542112328')

    def generic_bug(self, files):
        with NamedTemporaryFile() as f:
            args, db = bootstrap_file(f, m(V), '5')
            bootstrap_file(f, m(V), '5', mm(DEV), configurator=default)
            for file in files:
                args, db = bootstrap_file(f, m(V), '5', mm(DEV),
                                               'monitor', mm(FAST),
                                               'data/test/source/personal/andrew@acooke.org_%s.fit' % file)
                monitor(args, db)
            # run('sqlite3 %s ".dump"' % f.name, shell=True)
            run_pipeline(db, PipelineType.STATISTIC, force=True, start='2018-01-01', n_cpu=1)
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
