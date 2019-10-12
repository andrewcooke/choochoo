
from logging import getLogger

from .args import SUB_COMMAND, NEW, TYPE, ITEM, DATE, FORCE, ADD, COMPONENT, PART, STATISTICS, NAME1, NAME2
from ..lib import format_time, time_to_local_time
from ..squeal.tables.kit import KitType, KitItem, KitComponent, KitPart, find_name

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
            new(s, args[TYPE], args[ITEM], args[DATE], args[FORCE])
        elif cmd == ADD:
            add(s, args[ITEM], args[COMPONENT], args[PART], args[DATE], args[FORCE])
        elif cmd == STATISTICS:
            statistics(s, args[NAME1], args[NAME2])


def new(s, type, item, date, force):
    type_instance = KitType.get(s, type, force)
    item_instance = KitItem.new(s, type_instance, item)
    log.info(f'Created {type_instance.name} {item_instance.name}')


def add(s, item, component, part, date, force):
    item_instance = KitItem.get(s, item)
    component_instance = KitComponent.get(s, component, force)
    part_instance = KitPart.add(s, item_instance, component_instance, part, date, force)
    log.info(f'Added {item_instance.name} {component_instance.name} {part_instance.name} '
             f'at {time_to_local_time(part_instance.time_added(s))}')


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
            if isinstance(instance1, KitType):
                type_statistics(s, instance1)
            elif isinstance(instance1, KitComponent):
                component_statistics(s, instance1)
            else:
                raise Exception(f'Statistics are not supported for {type(instance1).SIMPLE_NAME}')
    else:
        raise Exception(f'Could not find "{name}"')


def type_statistics(s, type):
    log.info('type')


def component_statistics(s, component):
    log.info('component')


def item_part_statistics(s, item, part):
    log.info('item part')


