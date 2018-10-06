
from .database import add, Counter
from ..lib.date import YEAR, MONTH
from ..squeal.tables.activity import Activity
from ..squeal.tables.constant import Constant
from ..squeal.tables.statistic import Statistic, StatisticType, StatisticPipeline
from ..squeal.tables.topic import Topic, TopicField
from ..stoats.activity import ActivityStatistics
from ..stoats.clean import CleanUnusedStatistics
from ..stoats.names import BPM, FTHR
from ..stoats.summary import SummaryStatistics
from ..uweird.fields import Text, Float, Score, Integer

BIKE = 'Bike'
RUN = 'Run'


def default(db):

    with db.session_context() as s:

        # statistics pipeline

        c = Counter()
        s.add(StatisticPipeline(cls=ActivityStatistics, sort=c()))
        s.add(StatisticPipeline(cls=SummaryStatistics, kargs={'spec': 'm'}, sort=c()))
        s.add(StatisticPipeline(cls=SummaryStatistics, kargs={'spec': 'y'}, sort=c()))
        s.add(StatisticPipeline(cls=CleanUnusedStatistics, sort=c()))

        # basic activities

        bike = add(s, Activity(name='Bike', description='All cycling activities'))
        run = add(s, Activity(name='Run', description='All running activities'))
        s.flush()  # set IDs

        # constants used by statistics

        fthr_bike = add(s, Statistic(name=FTHR, owner=Constant, units=BPM,
                                     constraint=bike.id,
                                     description='''Heart rate at functional threshold (cycling).
                                     See https://www.britishcycling.org.uk/knowledge/article/izn20140808-Understanding-Intensity-2--Heart-Rate-0'''))
        s.add(Constant(type=StatisticType.INTEGER, name='%s.%s' % (FTHR, BIKE), statistic=fthr_bike))

        fthr_run = add(s, Statistic(name=FTHR, owner=Constant, units=BPM,
                                    constraint=run.id,
                                    description='''Heart rate at functional threshold (running).
                                    See https://www.britishcycling.org.uk/knowledge/article/izn20140808-Understanding-Intensity-2--Heart-Rate-0'''))
        s.add(Constant(type=StatisticType.INTEGER, name='%s.%s' % (FTHR, RUN), statistic=fthr_run))

        # a basic diary

        c = Counter()
        diary = add(s, Topic(name='Diary'))

        s.add(TopicField(topic=diary, sort=c(), type=StatisticType.TEXT,
                         display_cls=Text,
                         statistic=add(s, Statistic(name='Notes', owner=diary))))

        s.add(TopicField(topic=diary, sort=c(), type=StatisticType.FLOAT,
                         display_cls=Integer, display_kargs={'lo': 25, 'hi': 75},
                         statistic=add(s, Statistic(name='Rest HR', owner=diary, units='kg', summary='[avg]'))))
        s.add(TopicField(topic=diary, sort=c(), type=StatisticType.FLOAT,
                         display_cls=Float, display_kargs={'lo': 40, 'hi': 100, 'format': '%f2.1'},
                         statistic=add(s, Statistic(name='Weight', owner=diary, units='kg', summary='[avg]'))))
        s.add(TopicField(topic=diary, sort=c(), type=StatisticType.FLOAT,
                         display_cls=Float, display_kargs={'lo': 0, 'hi': 24, 'format': '%f2.1'},
                         statistic=add(s, Statistic(name='Sleep', owner=diary, units='hr', summary='[avg]'))))
        s.add(TopicField(topic=diary, sort=c(), type=StatisticType.INTEGER,
                         display_cls=Score,
                         statistic=add(s, Statistic(name='Mood', owner=diary, summary='[avg]'))))

        s.add(TopicField(topic=diary, sort=c(), type=StatisticType.TEXT,
                         display_cls=Text,
                         statistic=add(s, Statistic(name='Medication', owner=diary))))
