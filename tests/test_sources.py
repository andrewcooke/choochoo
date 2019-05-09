
from logging import getLogger
from subprocess import run
from tempfile import NamedTemporaryFile
from unittest import TestCase

from sqlalchemy.sql.functions import count

from ch2.commands.args import m, V, bootstrap_file
from ch2.config.personal import acooke
from ch2.lib.date import to_date
from ch2.squeal.tables.source import Source, Interval
from ch2.squeal.tables.statistic import StatisticJournalText, StatisticJournal, StatisticJournalFloat, StatisticName, \
    StatisticJournalInteger, StatisticJournalType
from ch2.squeal.tables.topic import TopicJournal, Topic
from ch2.squeal.utils import add
from ch2.stoats.calculate.summary import SummaryCalculator

log = getLogger(__name__)


# the idea here is to test the new database schema with sources etc
# so we configure a database then load some data, calculate some stats,
# and see if everything works as expected.

class TestSources(TestCase):

    def test_sources(self):

        with NamedTemporaryFile() as f:

            args, db = bootstrap_file(f, m(V), '5', configurator=acooke)

            with db.session_context() as s:

                # add a diary entry

                diary = s.query(Topic).filter(Topic.name == 'Diary').one()
                d = add(s, TopicJournal(topic=diary, date='2018-09-29'))
                d.populate(log, s)
                self.assertEqual(len(d.topic.fields), 9, list(enumerate(map(str, d.topic.fields))))
                self.assertEqual(d.topic.fields[0].statistic_name.name, 'Notes')
                self.assertEqual(d.topic.fields[1].statistic_name.name, 'Weight', str(d.topic.fields[1]))
                for field in d.topic.fields:
                    if field in d.statistics:
                        self.assertTrue(d.statistics[field].value is None, field)
                d.statistics[d.topic.fields[0]].value = 'hello world'
                d.statistics[d.topic.fields[1]].value = 64.5

            with db.session_context() as s:

                # check the diary entry was persisted

                diary = s.query(Topic).filter(Topic.name == 'Diary').one()
                d = s.query(TopicJournal).filter(TopicJournal.topic == diary,
                                                 TopicJournal.date == '2018-09-29').one()
                s.flush()
                d.populate(log, s)
                self.assertEqual(len(d.topic.fields), 9, list(enumerate(map(str, d.topic.fields))))
                self.assertEqual(d.topic.fields[0].statistic_name.name, 'Notes')
                self.assertEqual(d.statistics[d.topic.fields[0]].value, 'hello world')
                self.assertEqual(d.topic.fields[1].statistic_name.name, 'Weight')
                self.assertEqual(d.statistics[d.topic.fields[1]].value, 64.5)
                self.assertEqual(d.statistics[d.topic.fields[1]].type, StatisticJournalType.FLOAT)

            # generate summary stats

            SummaryCalculator(db, schedule='m').run()
            SummaryCalculator(db, schedule='y').run()

            with db.session_context() as s:

                # check the summary stats

                diary = s.query(Topic).filter(Topic.name == 'Diary').one()
                weight = s.query(StatisticJournal).join(StatisticName). \
                    filter(StatisticName.owner == diary, StatisticName.name == 'Weight').one()
                self.assertEqual(weight.value, 64.5)
                self.assertEqual(len(weight.measures), 2, weight.measures)
                self.assertEqual(weight.measures[0].rank, 1)
                self.assertEqual(weight.measures[0].percentile, 100, weight.measures[0].percentile)
                n = s.query(count(StatisticJournalFloat.id)).scalar()
                self.assertEqual(n, 4, n)
                n = s.query(count(StatisticJournalInteger.id)).scalar()
                self.assertEqual(n, 11, n)
                m_avg = s.query(StatisticJournalFloat).join(StatisticName). \
                    filter(StatisticName.name == 'Avg/Month Weight').one()
                self.assertEqual(m_avg.value, 64.5)
                y_avg = s.query(StatisticJournalFloat).join(StatisticName). \
                    filter(StatisticName.name == 'Avg/Year Weight').one()
                self.assertEqual(y_avg.value, 64.5)
                month = s.query(Interval).filter(Interval.schedule == 'm').one()
                self.assertEqual(month.start, to_date('2018-09-01'), month.start)
                self.assertEqual(month.finish, to_date('2018-10-01'), month.finish)

            with db.session_context() as s:

                # delete the diary entry

                diary = s.query(Topic).filter(Topic.name == 'Diary').one()
                d = s.query(TopicJournal).filter(TopicJournal.topic == diary,
                                                 TopicJournal.date == '2018-09-29').one()
                s.delete(d)

            run('sqlite3 %s ".dump"' % f.name, shell=True)

            with db.session_context() as s:

                # check the delete cascade

                self.assertEqual(s.query(count(TopicJournal.id)).scalar(), 0)
                # this should be zero because the Intervals were automatically deleted
                for source in s.query(Source).all():
                    print(source)
                for journal in s.query(StatisticJournal).all():
                    print(journal)
                self.assertEqual(s.query(count(Source.id)).scalar(), 11, list(map(str, s.query(Source).all())))  # constants
                self.assertEqual(s.query(count(StatisticJournalText.id)).scalar(), 7, s.query(count(StatisticJournalText.id)).scalar())
                self.assertEqual(s.query(count(StatisticJournal.id)).scalar(), 7, s.query(count(StatisticJournal.id)).scalar())
