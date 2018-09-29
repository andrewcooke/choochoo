
from ..squeal.tables.constant import Constant
from ..squeal.tables.activity import Activity
from ..squeal.tables.statistic import Statistic, StatisticType
from ..squeal.tables.topic import Topic, TopicField


def default(config):
    with config.session_context() as s:
        fthr = s.add(Constant(type=StatisticType.INTEGER,
                              statistic=s.add(Statistic(name='FTHR'))))
        diary = s.add(Topic(name='Diary'))
        s.add(TopicField(topic=diary, type=StatisticType.TEXT,
                         statistic=s.add(Statistic(name='Notes'))))
        bike = s.add(Activity(name='Bike', description='All cycling activities'))
