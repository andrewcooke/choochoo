
import datetime as dt
from sqlite3 import connect, Row

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from choochoo.squeal.diary import Diary
from choochoo.squeal.injury import InjuryDiary, Injury
from choochoo.squeal.schedule import Schedule, ScheduleDiary, ScheduleType


old = connect('/home/andrew/.ch2/database.sql')
old.row_factory = Row
new = create_engine('sqlite:////home/andrew/.ch2/database.sqla', echo=True)
session = sessionmaker(bind=new)()


def assert_empty(cls):
    assert session.query(cls).count() == 0, cls


assert_empty(Diary)
assert_empty(Injury)
assert_empty(InjuryDiary)
assert_empty(ScheduleType)
assert_empty(Schedule)
assert_empty(ScheduleDiary)

for row in old.execute('''select ordinal, notes, rest_hr, sleep, mood, weather, meds, weight from diary''', []):
    session.add(Diary(date=dt.date.fromordinal(row['ordinal']), notes=row['notes'], rest_hr=row['rest_hr'],
                      sleep=row['sleep'], mood=row['mood'], weather=row['weather'], medication=row['meds'],
                      weight=row['weight']))
session.flush()
session.commit()
