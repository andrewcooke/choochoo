
from subprocess import run
from tempfile import NamedTemporaryFile

from ch2.command.activity import activity
from ch2.command.constant import constant
from ch2.config.default import default
from ch2.command.args import bootstrap_file, m, V, DEV, mm
from ch2.stoats import run_statistics


def test_activities():

    with NamedTemporaryFile() as f:

        bootstrap_file(f, m(V), '5', mm(DEV), configurator=default)

        args, log, db = bootstrap_file(f, m(V), '5', 'constant', '--set', 'FTHR.%', '154')
        constant(args, log)

        args, log, db = bootstrap_file(f, m(V), '5', 'constant', 'FTHR.%')
        constant(args, log)

        args, log, db = bootstrap_file(f, m(V), '5', mm(DEV),
                                       'activity', 'Bike', 'data/test/personal/2018-08-27-rec.fit')
        activity(args, log)

        # run('sqlite3 %s ".dump"' % f.name, shell=True)

        run_statistics(log, db, force=True, after='2018-12-01')
        run_statistics(log, db, force=True, after='2018-01-01')

        run('sqlite3 %s ".dump"' % f.name, shell=True)

