
from ..squeal.tables.activity import Activity
from ..squeal.tables.statistic import Statistic, StatisticType
from ..squeal.tables.topic import Topic, TopicStatistic


def default(config):
    with config.session_context() as s:
        diary = s.add(Topic(name='Diary'))
        s.add(TopicStatistic(topic=diary, type=StatisticType.TEXT,
                             statistic=s.add(Statistic(name='Notes'))))
        bike = s.add(Activity(name='Bike', description='All cycling activities'))
