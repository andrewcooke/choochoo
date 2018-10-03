
from ..squeal.tables.activity import Activity
from ..squeal.tables.constant import Constant
from ..squeal.tables.statistic import Statistic, StatisticType, StatisticPipeline
from ..squeal.tables.topic import Topic, TopicField
from ..stoats.activity import ActivityStatistics
from ..stoats.names import BPM, FTHR
from ..stoats.summary import SummaryStatistics


BIKE = 'Bike'
RUN = 'Run'


def default(db):

    with db.session_context() as s:

        # statistics pipeline

        s.add(StatisticPipeline(cls=ActivityStatistics, sort=10))
        s.add(StatisticPipeline(cls=SummaryStatistics, sort=100))

        # basic activities

        bike = Activity(name='Bike', description='All cycling activities')
        s.add(bike)
        run = Activity(name='Run', description='All running activities')
        s.add(run)
        s.flush()  # set IDs

        # constants used by statistics

        fthr_bike = Statistic(name=FTHR, owner=Constant, units=BPM,
                              constraint=bike.id,
                              description='''Heart rate at functional threshold (cycling).
See https://www.britishcycling.org.uk/knowledge/article/izn20140808-Understanding-Intensity-2--Heart-Rate-0''')
        s.add(fthr_bike)
        s.add(Constant(type=StatisticType.INTEGER, name='%s.%s' % (FTHR, BIKE), statistic=fthr_bike))

        fthr_run = Statistic(name=FTHR, owner=Constant, units=BPM,
                             constraint=run.id,
                             description='''Heart rate at functional threshold (running).
See https://www.britishcycling.org.uk/knowledge/article/izn20140808-Understanding-Intensity-2--Heart-Rate-0''')
        s.add(fthr_run)
        s.add(Constant(type=StatisticType.INTEGER, name='%s.%s' % (FTHR, RUN), statistic=fthr_run))

        # a basic diary

        diary = Topic(name='Diary')
        s.add(diary)
        notes = Statistic(name='Notes', owner=diary)
        s.add(notes)
        s.add(TopicField(topic=diary, sort=10, type=StatisticType.TEXT, statistic=notes))
        sleep = Statistic(name='Sleep', owner=diary, units='hr', summary='[avg]')
        s.add(sleep)
        s.add(TopicField(topic=diary, sort=20, type=StatisticType.FLOAT, statistic=sleep))


