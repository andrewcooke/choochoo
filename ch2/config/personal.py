
from .default import default
from ..squeal.tables.topic import Topic


def acooke(db):
    default(db)
    with db.session_context() as s:
        injuries = Topic(name='Injuries')
        s.add(injuries)
        ms = Topic(parent=injuries, name='Multiple Sclerosis')
        s.add(ms)
        s.add(Topic(parent=ms, name='Betaferon', repeat='2018-08-07/2d'))  # reminder to take meds on alternate days
        leg = Topic(parent=injuries, name='Broken Femur LHS', start='2018-03-11')
        s.add(leg)
        s.add(Topic(parent=leg, name='Learn to manage tendon pain'))
        s.add(Topic(parent=leg, name='Maintain fitness'))
        s.add(Topic(parent=leg, name='Visit UK', finish='2018-08-11'))
