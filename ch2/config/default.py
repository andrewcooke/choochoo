
from ..squeal.tables.topic import TopicGroup


def default(config):
    with config.session_context() as s:
        s.add(TopicGroup(name='Reminder'))
        s.add(TopicGroup(name='Aim'))
