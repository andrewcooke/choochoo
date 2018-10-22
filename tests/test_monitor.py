
from tempfile import NamedTemporaryFile

import sqlalchemy.sql.functions as func

from ch2 import monitor
from ch2.command.args import bootstrap_file, m, V, DEV, mm, FAST
from ch2.config.default import default
from ch2.lib.date import to_time, to_date
from ch2.squeal.tables.monitor import MonitorJournal, MonitorSteps
from ch2.squeal.tables.pipeline import PipelineType
from ch2.squeal.tables.source import Source, SourceType, Interval
from ch2.squeal.tables.statistic import StatisticJournal, Statistic
from ch2.stoats.calculate import run_pipeline_after
from ch2.stoats.calculate.monitor import MonitorStatistics
from ch2.stoats.names import STEPS, REST_HR


def test_monitor():

    with NamedTemporaryFile() as f:

        args, log, db = bootstrap_file(f, m(V), '5')

        bootstrap_file(f, m(V), '5', mm(DEV), configurator=default)

        args, log, db = bootstrap_file(f, m(V), '5', mm(DEV),
                                       'monitor', mm(FAST), 'data/test/personal/25822184777.fit')
        monitor(args, log, db)

        # run('sqlite3 %s ".dump"' % f.name, shell=True)

        run_pipeline_after(log, db, PipelineType.STATISTIC, force=True, after='2018-01-01')

        # run('sqlite3 %s ".dump"' % f.name, shell=True)

        with db.session_context() as s:
            n = s.query(func.count(StatisticJournal.id)).scalar()
            assert n == 10, n
            mjournal = s.query(MonitorJournal).one()
            assert mjournal.time != mjournal.finish


def test_values():

    with NamedTemporaryFile() as f:

        args, log, db = bootstrap_file(f, m(V), '5')

        bootstrap_file(f, m(V), '5', mm(DEV), configurator=default)

        for file in ('24696157869', '24696160481', '24696163486'):
            args, log, db = bootstrap_file(f, m(V), '5', mm(DEV),
                                           'monitor', mm(FAST), 'data/test/personal/andrew@acooke.org_%s.fit' % file)
            monitor(args, log, db)

        # run('sqlite3 %s ".dump"' % f.name, shell=True)

        run_pipeline_after(log, db, PipelineType.STATISTIC, force=True, after='2018-01-01')

        # run('sqlite3 %s ".dump"' % f.name, shell=True)

        with db.session_context() as s:
            mjournals = s.query(MonitorJournal).order_by(MonitorJournal.time).all()
            assert mjournals[2].time == to_time('2018-09-06 15:06:00'), mjournals[2].time
            print(mjournals[2].fit_file)

            # steps

            steps = sorted(mjournals[2].steps, key=lambda x: x.time)
            # 72 without None skip at start
            assert len(steps) == 70, len(steps)
            # 136 without None
            assert steps[0].value == 9, steps[0].value
            # 355 without None
            assert steps[1].value == 1165, steps[1].value
            total = sum(s.value for s in steps)
            # 12757 without None
            assert total == 11066, total
            summary = s.query(StatisticJournal).join(Statistic, Source, Interval). \
                filter(Source.type == SourceType.INTERVAL,
                       Source.time == to_date('2018-09-06'),
                       Interval.schedule == 'd',
                       Statistic.owner == MonitorStatistics,
                       Statistic.name == STEPS).one()
            # connect has 12757 for this date, which matches the number above.
            # seems they're using files rather than splitting by date
            # looking at file, they seem to stop at 3am
            # 12601 without None
            assert summary.value == 10888, summary.value
            check = s.query(func.sum(MonitorSteps.value)). \
                filter(MonitorSteps.time >= to_time('2018-09-06 03:00'),
                       MonitorSteps.time < to_time('2018-09-07 03:00')).scalar()
            # still doesn't match but close
            assert check == 12735, check

            # heart rate

            hrs = sorted(mjournals[2].heart_rate, key=lambda x: x.time)
            assert len(hrs) == 571, len(hrs)
            assert hrs[0].value == 74, hrs[0].value
            hrs = [hr.value for hr in hrs]
            assert min(*hrs) == 0, min(*hrs)
            hrs = [hr for hr in hrs if hr > 0]
            assert min(*hrs) == 52, min(*hrs)
            summary = s.query(StatisticJournal).join(Statistic, Source, Interval). \
                filter(Source.type == SourceType.INTERVAL,
                       Source.time == to_date('2018-09-06'),
                       Interval.schedule == 'd',
                       Statistic.owner == MonitorStatistics,
                       Statistic.name == REST_HR).one()
            assert summary.value == 42, summary.value


def test_bug():

     with NamedTemporaryFile() as f:

        args, log, db = bootstrap_file(f, m(V), '5')

        bootstrap_file(f, m(V), '5', mm(DEV), configurator=default)

        for file in ('25505915679', '25519562859', '25519565531', '25532154264', '25539076032', '25542112328'):
            args, log, db = bootstrap_file(f, m(V), '5', mm(DEV),
                                           'monitor', mm(FAST), 'data/test/personal/andrew@acooke.org_%s.fit' % file)
            monitor(args, log, db)

        # run('sqlite3 %s ".dump"' % f.name, shell=True)

        run_pipeline_after(log, db, PipelineType.STATISTIC, force=True, after='2018-01-01')

        # run('sqlite3 %s ".dump"' % f.name, shell=True)

        with db.session_context() as s:
            mjournals = s.query(MonitorJournal).order_by(MonitorJournal.time).all()

            # steps

            total = 0
            for mj in mjournals:
                sub = sum(s.value for s in mj.steps if to_date(s.time) == to_date('2018-10-07'))
                print(sub, mj.fit_file)
                print(min(s.time for s in mj.steps), max(s.time for s in mj.steps))
                total += sub
            assert total == 3025, total

            summary = s.query(StatisticJournal).join(Statistic, Source, Interval). \
                filter(Source.type == SourceType.INTERVAL,
                       Source.time == to_date('2018-10-07'),
                       Interval.schedule == 'd',
                       Statistic.owner == MonitorStatistics,
                       Statistic.name == STEPS).one()
            # connect has 3031 for this date.  again, close
            assert summary.value == 3025, summary.value
