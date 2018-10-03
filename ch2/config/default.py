
from ..squeal.tables.activity import Activity
from ..squeal.tables.constant import Constant
from ..squeal.tables.statistic import Statistic, StatisticType, StatisticPipeline
from ..squeal.tables.topic import Topic, TopicField
from ..stoats.activity import ActivityStatistics
from ..stoats.names import BPM
from ..stoats.summary import SummaryStatistics


def default(config):

    with config.session_context() as s:

        # statistics pipeline

        s.add(StatisticPipeline(cls=ActivityStatistics, sort=10))
        s.add(StatisticPipeline(cls=SummaryStatistics, sort=100))

        # constants used by statistics

        s.add(Constant(type=StatisticType.INTEGER,
                       statistic=s.add(Statistic(name='FTHR', owner=Constant, units=BPM,
                                                 description='''Heart rate at functional threshold.
See https://www.britishcycling.org.uk/knowledge/article/izn20140808-Understanding-Intensity-2--Heart-Rate-0'''))))

        # a basic diary

        diary = s.add(Topic(name='Diary'))
        s.add(TopicField(topic=diary, sort=10, type=StatisticType.TEXT,
                         statistic=s.add(Statistic(name='Notes', owner=diary))))
        s.add(TopicField(topic=diary, sort=20, type=StatisticType.FLOAT,
                         statistic=s.add(Statistic(name='Sleep', owner=diary,
                                                   units='hr', summary='[avg]'))))

        # basic activities

        s.add(Activity(name='Bike', description='All cycling activities'))
        s.add(Activity(name='Run', description='All running activities'))

