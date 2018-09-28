
from subprocess import run
from tempfile import NamedTemporaryFile

from ch2.config.database import config
from ch2.config.personal import acooke
from ch2.squeal.tables.activity import Activity, ActivityDiary
from ch2.squeal.tables.statistic import Statistic, StatisticValue


def test_config():
    with NamedTemporaryFile() as f:
        c = config('--database', f.name, '-v', '5')
        acooke(c)
        dump(f.name)


def test_stats():
    with NamedTemporaryFile() as f:
        c = config('--database', f.name, '-v', '5')
        acooke(c)
        with c.session_context() as s:
            activity = s.all(Activity, Activity.name == 'Bike')[0]
            diary = s.add(ActivityDiary(date='2018-01-01', activity=activity, name='Diary entry',
                          start='2018-01-01T10:00', finish='2018-01-01T10:10', fit_file='xxx'))
            statistic = s.add(Statistic(cls=ActivityDiary.__tablename__,
                                        cls_constraint=activity.id,
                                        name="example", namespace=''))
            s.add(StatisticValue(statistic=statistic, value=42, time=diary.date))
        with c.session_context() as s:
            diary = s.all(ActivityDiary)[0]
            diary.populate_statistics(s.session)
            assert diary.statistics.example.value == 42, diary.statistics.example



def dump(path):
    run('sqlite3 %s ".dump"' % path, shell=True)
