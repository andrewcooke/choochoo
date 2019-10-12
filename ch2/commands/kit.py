
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
            statistics(s, args[NAME], args[COMPONENT])


def new(s, group, item, date, force):
    # TODO - dates and statistics for items
    group_instance = KitGroup.get(s, group, force)
    item_instance = KitItem.new(s, group_instance, item)
    log.info(f'Created {group_instance.name} {item_instance.name}')


def add(s, item, component, part, date, force):
    item_instance = KitItem.get(s, item)
    component_instance = KitComponent.get(s, component, force)
    model_instance = KitModel.add(s, item_instance, component_instance, part, date, force)
    log.info(f'Added {item_instance.name} {component_instance.name} {model_instance.name} '
             f'at {time_to_local_time(model_instance.time_added(s))}')


def statistics(s, name, component):
    instance1 = find_name(s, name)
    if instance1:
        if component:
            if isinstance(instance1, KitItem):
                instance2 = find_name(s, component)
                if instance2:
                    if isinstance(instance2, KitComponent):
                        item_part_statistics(s, instance1, instance2)
                    else:
                        raise Exception('Second name must be a component')
                else:
                    raise Exception(f'Could not find "{component}"')
            else:
                raise Exception('First name must be an item')
        else:
            if isinstance(instance1, KitGroup):
                group_statistics(s, instance1)
            elif isinstance(instance1, KitComponent):
                component_statistics(s, instance1)
            else:
                raise Exception(f'Statistics are not supported for {type(instance1).SIMPLE_NAME}')
    else:
        raise Exception(f'Could not find "{name}"')


def group_statistics(s, group):
    log.info('group')


def component_statistics(s, component):
    log.info('component')


def item_part_statistics(s, item, part):
    log.info('item part')


