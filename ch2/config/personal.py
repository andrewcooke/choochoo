
from .default import default
from ..squeal.tables.topic import Topic


def acooke(config):
    default(config)
    with config.session_context() as s:
        injuries = s.add(Topic(name='Injuries'))
        ms = s.add(Topic(parent=injuries, name='Multiple Sclerosis'))
        s.add(Topic(parent=ms, name='Betaferon', repeat='2018-08-07/2d'))  # reminder to take meds on alternate days
        leg = s.add(Topic(parent=injuries, name='Broken Femur LHS', start='2018-03-11'))
        s.add(Topic(parent=leg, name='Learn to manage tendon pain'))
        s.add(Topic(parent=leg, name='Maintain fitness'))
        s.add(Topic(parent=leg, name='Visit UK', finish='2018-08-11'))
