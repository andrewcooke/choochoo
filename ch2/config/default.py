
from ..stoats.names import BPM
from ..squeal.tables.constant import Constant
from ..squeal.tables.activity import Activity
from ..squeal.tables.statistic import Statistic, StatisticType
from ..squeal.tables.topic import Topic, TopicField


def default(config):
    with config.session_context() as s:
        fthr = s.add(Constant(type=StatisticType.INTEGER,
                              statistic=s.add(Statistic(name='FTHR', owner=Constant, units=BPM))))
        diary = s.add(Topic(name='Diary'))
        s.add(TopicField(topic=diary, sort=10, type=StatisticType.TEXT,
                         statistic=s.add(Statistic(name='Notes', owner=diary))))
        s.add(TopicField(topic=diary, sort=20, type=StatisticType.FLOAT,
                         statistic=s.add(Statistic(name='Sleep', owner=diary,
                                                   units='hr', summary='[avg]'))))
        bike = s.add(Activity(name='Bike', description='All cycling activities'))
