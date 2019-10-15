
from logging import getLogger

from .args import SUB_COMMAND, NEW, GROUP, ITEM, DATE, FORCE, ADD, COMPONENT, MODEL, STATISTICS, NAME
from ..lib import time_to_local_time
from ..squeal.tables.kit import KitGroup, KitItem, KitComponent, KitModel, find_name

log = getLogger(__name__)


def kit(args, db):
    '''
## kit

    > ch2 kit new bike cotic
    > ch2 kit add cotic chain pc1110 2019-10-12
    > ch2 kit retire cotic chain
    > ch2 kit show cotic
    > ch2 kit statistics cotic chain
    > ch2 kit statistics chain
    > ch2 kit statistics bike
    > ch2 kit delete cotic chain 2019-10-12
    > ch2 kit delete cotic

    > ch2 kit new shoe 'red adidas'
    > ch2 kit retire 'red adidas'

Some of the above will require --force to confirm.
    '''
    cmd = args[SUB_COMMAND]
    with db.session_context() as s:
        if cmd == NEW:
            new(s, args[GROUP], args[ITEM], args[DATE], args[FORCE])
        elif cmd == ADD:
            add(s, args[ITEM], args[COMPONENT], args[MODEL], args[DATE], args[FORCE])
        elif cmd == STATISTICS:
            statistics(s, args[NAME])


def new(s, group, item, date, force):
    group_instance = KitGroup.get(s, group, force)
    item_instance = KitItem.new(s, group_instance, item, date)
    log.info(f'Created {group_instance.name} {item_instance.name}'
             f'at {time_to_local_time(item_instance.time_added(s))}')


def add(s, item, component, part, date, force):
    item_instance = KitItem.get(s, item)
    component_instance = KitComponent.get(s, component, force)
    model_instance = KitModel.add(s, item_instance, component_instance, part, date, force)
    log.info(f'Added {item_instance.name} {component_instance.name} {model_instance.name} '
             f'at {time_to_local_time(model_instance.time_added(s))}')


def statistics(s, name):
    instance = find_name(s, name)
    {KitGroup: group_statistics,
     KitItem: item_statistics,
     KitComponent: component_statistics,
     KitModel: model_statistics}[type(instance)](s, instance)


def group_statistics(s, group):
    log.info('group')


def item_statistics(s, item):
    log.info('item')


def component_statistics(s, component):
    log.info('component')


def model_statistics(s, model):
    log.info('model')
