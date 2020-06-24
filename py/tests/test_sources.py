
from logging import getLogger
from tempfile import TemporaryDirectory
from tests import LogTestCase

from sqlalchemy.sql.functions import count

from ch2.commands.args import m, V, bootstrap_dir
from ch2.config.profile.acooke import acooke
from ch2.lib.date import to_date
from ch2.sql.tables.source import Source, Interval
from ch2.sql.tables.statistic import StatisticJournalText, StatisticJournal, StatisticJournalFloat, StatisticName, \
    StatisticJournalInteger, StatisticJournalType
from ch2.sql.tables.topic import DiaryTopicJournal, DiaryTopic
from ch2.sql.utils import add
from ch2.pipeline.calculate.summary import SummaryCalculator

log = getLogger(__name__)


# the idea here is to test the new database schema with sources etc
# so we configure a database then load some data, calculate some stats,
# and see if everything works as expected.

class TestSources(LogTestCase):

    def test_sources(self):

        with TemporaryDirectory() as f:

            args, data = bootstrap_dir(f, m(V), '5', configurator=acooke)

            with data.db.session_context() as s:

                # add a diary entry

                journal = add(s, DiaryTopicJournal(date='2018-09-29'))
                cache = journal.cache(s)
                diary = s.query(DiaryTopic).filter(DiaryTopic.title == 'Status').one()
                fields = diary.fields
                self.assertEqual(len(fields), 6, list(enumerate(map(str, fields))))
                self.assertEqual(fields[0].statistic_name.name, 'notes')
                self.assertEqual(fields[1].statistic_name.name, 'weight', str(fields[1]))
                statistics = [cache[field] for field in fields]
                for statistic in statistics:
                    self.assertTrue(statistic.value is None, statistics)
                statistics[0].value = 'hello world'
                statistics[1].value = 64.5

            with data.db.session_context() as s:

                # check the diary entry was persisted

                journal = DiaryTopicJournal.get_or_add(s, '2018-09-29')
                cache = journal.cache(s)
                diary = s.query(DiaryTopic).filter(DiaryTopic.title == 'Status').one()
                fields = diary.fields
                self.assertEqual(len(fields), 6, list(enumerate(map(str, fields))))
                self.assertEqual(fields[0].statistic_name.name, 'notes')
                self.assertEqual(fields[1].statistic_name.name, 'weight', str(fields[1]))
                statistics = [cache[field] for field in fields]
                self.assertEqual(statistics[1].value, 64.5)
                self.assertEqual(statistics[1].type, StatisticJournalType.FLOAT)

            # generate summary stats

            SummaryCalculator(data, schedule='m').run()
            SummaryCalculator(data, schedule='y').run()

            with data.db.session_context() as s:

                # check the summary stats

                diary = s.query(DiaryTopic).filter(DiaryTopic.title == 'Status').one()
                weights = s.query(StatisticJournal).join(StatisticName). \
                               filter(StatisticName.owner == diary, StatisticName.name == 'weight'). \
                               order_by(StatisticJournal.time).all()
                self.assertEqual(len(weights), 2)
                self.assertEqual(weights[1].value, 64.5)
                self.assertEqual(len(weights[1].measures), 2, weights[1].measures)
                self.assertEqual(weights[1].measures[0].rank, 1)
                self.assertEqual(weights[1].measures[0].percentile, 100, weights[1].measures[0].percentile)
                n = s.query(count(StatisticJournalFloat.id)).scalar()
                self.assertEqual(n, 4, n)
                n = s.query(count(StatisticJournalInteger.id)).scalar()
                self.assertEqual(n, 6, n)
                m_avg = s.query(StatisticJournalFloat).join(StatisticName). \
                    filter(StatisticName.name == 'avg-month-weight').one()
                self.assertEqual(m_avg.value, 64.5)
                y_avg = s.query(StatisticJournalFloat).join(StatisticName). \
                    filter(StatisticName.name == 'avg-year-weight').one()
                self.assertEqual(y_avg.value, 64.5)
                month = s.query(Interval).filter(Interval.schedule == 'm').first()
                self.assertEqual(month.start, to_date('2018-09-01'), month.start)
                self.assertEqual(month.finish, to_date('2018-10-01'), month.finish)

            with data.db.session_context() as s:

                # delete the diary entry

                journal = DiaryTopicJournal.get_or_add(s, '2018-09-29')
                s.delete(journal)

            with data.db.session_context() as s:

                # check the delete cascade

                self.assertEqual(s.query(count(DiaryTopicJournal.id)).scalar(), 1)
                # this should be zero because the Intervals were automatically deleted
                # (well, now +1 because there's an original default weight)
                for source in s.query(Source).all():
                    print(source)
                for journal in s.query(StatisticJournal).all():
                    print(journal)
                self.assertEqual(s.query(count(Source.id)).scalar(), 37, list(map(str, s.query(Source).all())))  # constants
                self.assertEqual(s.query(count(StatisticJournalText.id)).scalar(), 13, s.query(count(StatisticJournalText.id)).scalar())
                self.assertEqual(s.query(count(StatisticJournal.id)).scalar(), 22, s.query(count(StatisticJournal.id)).scalar())
