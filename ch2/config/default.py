
from ..squeal.tables.schedule import ScheduleGroup


def default(config):
    with config.session_context() as s:
        s.add(ScheduleGroup(name='Reminder'))
        s.add(ScheduleGroup(name='Aim'))
