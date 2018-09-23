
from ch2.squeal.tables.activity import Activity
from ch2.squeal.tables.injury import Injury

from ..squeal.tables.schedule import ScheduleGroup, Schedule
from .default import default


def acooke(config):
    default(config)
    with config.session_context() as s:
        reminder = s.all(ScheduleGroup, ScheduleGroup.name == 'Reminder')[0]
        s.add(Schedule(group=reminder, repeat='2018-08-07/2d', name='Betaferon'))
        aim = s.all(ScheduleGroup, ScheduleGroup.name == 'Aim')[0]
        s.add(Schedule(group=aim, start='2018-03-11', name='Learn to manage tendon pain'))
        s.add(Schedule(group=aim, start='2018-03-11', name='Maintain fitness'))
        s.add(Activity(name='Bike', description='All cycling activities'))
        s.add(Injury(start='2018-03-11', name='Tendon pain (femur, lhs)',
                     description='Mainly irritation from over-long rod.  But also "deeper" pain.  And RHS?'))
        s.add(Injury(name='MS (General Notes)'))
