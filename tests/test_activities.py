
import datetime as dt
from subprocess import run
from tempfile import NamedTemporaryFile

from sqlalchemy.sql.functions import count

from ch2.command.activities import activities
from ch2.command.args import bootstrap_file, m, V, DEV, mm, FAST
from ch2.command.constant import constant
from ch2.config.default import default
from ch2.squeal.tables.activity import ActivityJournal
from ch2.squeal.tables.statistic import StatisticJournal
from ch2.stoats.calculate import run_statistics


def test_activities():

    with NamedTemporaryFile() as f:

        args, log, db = bootstrap_file(f, m(V), '5')

        bootstrap_file(f, m(V), '5', mm(DEV), configurator=default)

        args, log, db = bootstrap_file(f, m(V), '5', 'constant', '--set', 'FTHR.%', '154')
        constant(args, log)

        args, log, db = bootstrap_file(f, m(V), '5', 'constant', 'FTHR.%')
        constant(args, log)

        args, log, db = bootstrap_file(f, m(V), '5', mm(DEV),
                                       'activity', mm(FAST), 'Bike', 'data/test/personal/2018-08-27-rec.fit')
        activities(args, log)

        # run('sqlite3 %s ".dump"' % f.name, shell=True)

        run_statistics(log, db, force=True, after='2018-01-01')

        # run('sqlite3 %s ".dump"' % f.name, shell=True)

        with db.session_context() as s:
            n = s.query(count(StatisticJournal.id)).scalar()
            assert n == 27, n
            journal = s.query(ActivityJournal).one()
            assert journal.time != journal.finish

