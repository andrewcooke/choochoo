
from subprocess import run
from tempfile import NamedTemporaryFile

from ch2 import constant
from ch2.activities import add_activity
from ch2.args import bootstrap_file, m, V, DEV, mm
from ch2.config.default import default


def test_activities():

    with NamedTemporaryFile() as f:

        bootstrap_file(f, m(V), '5', mm(DEV), configurator=default)

        args, log, db = bootstrap_file(f, m(V), '5', 'constant', 'FTHR', '2010-01-01', '154')
        constant(args, log)

        args, log, db = bootstrap_file(f, m(V), '5', 'constant', 'FTHR')
        constant(args, log)

        args, log, db = bootstrap_file(f, m(V), '5', mm(DEV),
                                       'add-activity', 'Bike', 'data/test/personal/2018-08-27-rec.fit')
        add_activity(args, log)

        run('sqlite3 %s ".dump"' % f.name, shell=True)
