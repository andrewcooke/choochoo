
from tempfile import NamedTemporaryFile

from ch2.activities import add_activity
from ch2.args import bootstrap_file, m, V, DEV, mm
from ch2.config.default import default


def test_activities():

    with NamedTemporaryFile() as f:

        args, log, db = bootstrap_file(f, default, m(V), '5', mm(DEV),
                                       post_config=['add-activity', 'Bike', 'data/test/personal/2018-07-26-rec.fit'])
        add_activity(args, log)
