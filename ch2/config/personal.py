
from ch2.squeal.tables.activity import Activity
from ch2.squeal.tables.injury import Injury

from ..squeal.tables.topic import TopicGroup, Topic
from .default import default


def acooke(config):
    default(config)
    with config.session_context() as s:
        reminder = s.all(TopicGroup, TopicGroup.name == 'Reminder')[0]
        s.add(Topic(group=reminder, repeat='2018-08-07/2d', name='Betaferon'))
        aim = s.all(TopicGroup, TopicGroup.name == 'Aim')[0]
        s.add(Topic(group=aim, start='2018-03-11', name='Learn to manage tendon pain'))
        s.add(Topic(group=aim, start='2018-03-11', name='Maintain fitness'))
        s.add(Activity(name='Bike', description='All cycling activities'))
        s.add(Injury(start='2018-03-11', name='Tendon pain (femur, lhs)',
                     description='Mainly irritation from over-long rod.  But also "deeper" pain.  And RHS?'))
        s.add(Injury(name='MS (General Notes)'))
