from subprocess import run
from tempfile import NamedTemporaryFile

from ch2.config.database import config
from ch2.config.personal import acooke


def test_config():
    with NamedTemporaryFile() as f:
        c = config('--database', f.name, '-v', '5')
        acooke(c)
        dump(f.name)


def dump(path):
    run('sqlite3 %s ".dump"' % path, shell=True)
