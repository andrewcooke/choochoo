
from tempfile import NamedTemporaryFile

from sqlalchemy.sql.functions import count

from ch2.args import DATABASE, mm, m, V, NamespaceWithVariables, parser
from ch2.config.database import config
from ch2.config.personal import acooke
from ch2.log import make_log
from ch2.squeal.database import Database
from ch2.squeal.tables.source import Source
from ch2.squeal.tables.statistic import StatisticJournalText, StatisticJournal
from ch2.squeal.tables.topic import TopicJournal, Topic


# the idea here is to test the new database schema with sources etc
# so we configure a database then load some data, calculate some stats,
# and see if everything works as expected.


def test_sources():

    with NamedTemporaryFile() as f:

        args = [mm(DATABASE), f.name, m(V), '5']
        c = config(*args)
        acooke(c)

        # todo - this should be simpler
        p = parser()
        a = NamespaceWithVariables(p.parse_args(args))
        log = make_log(a)
        db = Database(a, log)

        with db.session_context() as s:

            diary = s.query(Topic).filter(Topic.name == 'Diary').one()
            d = TopicJournal(topic=diary, time='2018-09-29')
            s.add(d)
            assert len(d.topic.fields) == 1
            assert d.topic.fields[0].statistic.name == 'Notes'
            assert d.journal[d.topic.fields[0]].value == None
            d.journal[d.topic.fields[0]].value = 'hello world'

        with db.session_context() as s:

            diary = s.query(Topic).filter(Topic.name == 'Diary').one()
            d = s.query(TopicJournal).filter(TopicJournal.topic == diary,
                                             TopicJournal.time == '2018-09-29').one()
            assert len(d.topic.fields) == 1
            assert d.topic.fields[0].statistic.name == 'Notes'
            assert d.journal[d.topic.fields[0]].value == 'hello world'

            s.delete(d)

        with db.session_context() as s:

            assert s.query(count(TopicJournal.id)).scalar() == 0
            assert s.query(count(Source.id)).scalar() == 0
            assert s.query(count(StatisticJournalText.id)).scalar() == 0
            assert s.query(count(StatisticJournal.id)).scalar() == 0
