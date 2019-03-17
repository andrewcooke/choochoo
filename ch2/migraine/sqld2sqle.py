
from sqlite3 import connect, Row

from ch2.commands.args import bootstrap_file, m, V
from ch2.config.personal import acooke
from ch2.lib.date import to_time
from ch2.squeal.utils import add
from ch2.squeal.tables.source import Source
from ch2.squeal.tables.statistic import StatisticJournal, StatisticJournalText, StatisticJournalInteger, \
    StatisticJournalFloat, StatisticName
from ch2.squeal.tables.topic import TopicJournal, Topic

old = connect('/home/andrew/.ch2/database.sqld')
old.row_factory = Row


class File:
    name = '/home/andrew/.ch2/database.sqle'


args, db = bootstrap_file(File(), m(V), '5', configurator=acooke)
s = db.session()


def assert_empty(cls):
    assert s.query(cls).count() == 0, cls


assert_empty(Source)
assert_empty(StatisticJournal)
assert_empty(TopicJournal)


diary = s.query(Topic).filter(Topic.name == 'DailyDiary').one()
fields = dict((field.statistic_name.name, field.statistic_name) for field in diary.fields)
notes = fields['Notes']
mood = fields['Mood']
hr = fields['Rest HR']
weight = fields['Weight']
sleep = fields['Sleep']
weather = fields['Weather']
meds = fields['Medication']

for row in old.execute('''select date, notes, rest_heart_rate, sleep, mood, weather, medication, weight from diary''', []):
    if row['notes'] or row['mood'] or row['rest_heart_rate'] or row['weight'] or row['sleep'] or row['weather']:
        tj = add(s, TopicJournal(time=to_time(row['date']), topic=diary))
        if row['notes']:
            add(s, StatisticJournalText(statistic_name=notes, source=tj, value=row['notes']))
        if row['mood']:
            add(s, StatisticJournalInteger(statistic_name=mood, source=tj, value=row['mood']))
        if row['rest_heart_rate']:
            add(s, StatisticJournalInteger(statistic_name=hr, source=tj, value=row['rest_heart_rate']))
        if row['weight']:
            add(s, StatisticJournalFloat(statistic_name=weight, source=tj, value=row['weight']))
        if row['sleep']:
            add(s, StatisticJournalFloat(statistic_name=sleep, source=tj, value=row['sleep']))
        if row['weather']:
            add(s, StatisticJournalText(statistic_name=weather, source=tj, value=row['weather']))
        if row['medication']:
            add(s, StatisticJournalText(statistic_name=meds, source=tj, value=row['medication']))


def injury_notes(old_name, new_name):
    injury_id = next(old.execute('''select id from injury where name like ?''', [old_name]))[0]
    topic = s.query(Topic).filter(Topic.name == new_name).one()
    notes = s.query(StatisticName).filter(StatisticName.name == 'Notes', StatisticName.constraint == topic.id).one()
    for row in old.execute('''select date, notes from injury_diary where injury_id = ?''', [injury_id]):
        if row['notes']:
            # print(row['notes'], len(row['notes']))
            tj = add(s, TopicJournal(time=to_time(row['date']), topic=topic))
            add(s, StatisticJournalText(statistic_name=notes, source=tj, value=row['notes']))


injury_notes('MS (General Notes)', 'Multiple Sclerosis')
injury_notes('Tendon pain (femur, lhs)', 'Broken Femur LHS')

s.flush()
s.commit()
s.close()

print('end')
