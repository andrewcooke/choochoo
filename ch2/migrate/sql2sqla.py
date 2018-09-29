
import datetime as dt
from sqlite3 import connect, Row

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker



def date_or_null(ordinal):
    if ordinal is None:
        return None
    else:
        return dt.date.fromordinal(ordinal)


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

# preserve primary key for reference to injury_diary
for row in old.execute('''select id, start, finish, title, description, sort from injury'''):
    session.add(Injury(id=row['id'], start=date_or_null(row['start']), finish=date_or_null(row['finish']),
                       title=row['title'], description=row['description'], sort=row['sort']))
session.flush()
session.commit()

for row in old.execute('''select ordinal, injury, pain_avg, pain_peak, pain_freq, notes from injury_diary'''):
    session.add(InjuryDiary(date=dt.date.fromordinal(row['ordinal']), injury_id=row['injury'],
                            pain_average=row['pain_avg'], pain_peak=row['pain_peak'], pain_frequency=row['pain_freq'],
                            notes=row['notes']))
session.flush()
session.commit()

aim = ScheduleType(name='Aim')
session.add(aim)
reminder = ScheduleType(name='Reminder')
session.add(reminder)

session.add(Schedule(type=aim, title='Learn to manage tendon pain', has_notes=False))
session.add(Schedule(type=aim, title='Travel to UK', has_notes=False))
fitness = Schedule(type=aim, title='Maintain fitness', has_notes=False)
session.add(fitness)
session.add(Schedule(type=reminder, title='Betaferon', has_notes=False, repeat='2018-08-07/2d'))

session.add(ScheduleDiary(date=dt.date.fromordinal(736884), schedule=fitness, notes='Cycled today (10min)'))

session.flush()
session.commit()
