
from tempfile import NamedTemporaryFile

from sqlalchemy.sql.functions import count

from ch2 import monitor
from ch2.command.args import bootstrap_file, m, V, DEV, mm, FAST
from ch2.config.default import default
from ch2.lib.date import to_time, to_date
from ch2.squeal.tables.monitor import MonitorJournal
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
            n = s.query(count(StatisticJournal.id)).scalar()
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
            mjournal = s.query(MonitorJournal).order_by(MonitorJournal.time).all()
            assert mjournal[2].time == to_time('2018-09-06 15:06:00'), mjournal[2].time

            # steps

            steps = sorted(mjournal[2].steps, key=lambda x: x.time)
            assert len(steps) == 72, len(steps)
            assert steps[0].value == 1336, steps[0].value
            assert steps[1].value == 355, steps[1].value
            total = sum(s.value for s in steps)
            assert total == 12757, total
            summary = s.query(StatisticJournal).join(Statistic, Source, Interval). \
                filter(Source.type == SourceType.INTERVAL,
                       Source.time == to_date('2018-09-06'),
                       Interval.schedule == 'd',
                       Statistic.owner == MonitorStatistics,
                       Statistic.name == STEPS).one()
            # connect has 12757 for this date, which matches the number above.
            # seems they're using files rather than splitting by date
            assert summary.value == 12601, summary.value

            # heart rate

            hrs = sorted(mjournal[2].heart_rate, key=lambda x: x.time)
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
