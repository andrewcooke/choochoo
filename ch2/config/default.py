
from ..squeal.tables.activity import Activity


def default(config):
    with config.session_context() as s:
        bike = s.add(Activity(name='Bike', description='All cycling activities'))
        # todo - add stats for bike
