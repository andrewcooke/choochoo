
from .default import default
from ..config.database import add, Counter
from ..squeal.tables.statistic import StatisticType, Statistic
from ..squeal.tables.topic import Topic, TopicField
from ..uweird.fields import Text


def acooke(db):

    default(db)

    with db.session_context() as s:

        c = Counter()
        injuries = add(s, Topic(name='Injuries', sort=c()))
        ms = add(s, Topic(parent=injuries, name='Multiple Sclerosis', sort=c()))
        s.add(TopicField(topic=ms, sort=c(), type=StatisticType.TEXT,
                         display_cls=Text,
                         statistic=add(s, Statistic(name='Notes', owner=ms, constraint=ms.id))))
        s.add(Topic(parent=ms, name='Betaferon', schedule='2018-08-07/2d'))  # reminder to take meds on alternate days
        leg = add(s, Topic(parent=injuries, name='Broken Femur LHS', schedule='2018-03-11-'))
        s.add(TopicField(topic=leg, sort=c(), type=StatisticType.TEXT,
                         display_cls=Text,
                         statistic=add(s, Statistic(name='Notes', owner=leg, constraint=leg.id))))
        s.add(Topic(parent=leg, name='Learn to manage tendon pain'))
        s.add(Topic(parent=leg, name='Maintain fitness'))
        s.add(Topic(parent=leg, name='Visit UK', schedule='-2018-08-11'))
