
from logging import getLogger

from .args import SUB_COMMAND, NEW, TYPE, ITEM, DATE, FORCE, ADD, COMPONENT, PART
from ..lib import format_time, time_to_local_time
from ..squeal.tables.kit import KitType, KitItem, KitComponent, KitPart

log = getLogger(__name__)


def kit(args, db):
    '''
## kit

    > ch2 kit new bike cotic
    > ch2 kit add cotic chain pc1110 2019-10-12
    > ch2 kit show cotic
    > ch2 kit retire cotic chain
    > ch2 kit retire cotic
    > ch2 kit delete cotic chain 2019-10-12
    > ch2 kit delete cotic

    > ch2 kit new shoe 'red adidas'
    > ch2 kit retire 'red adidas'

Some of the above will require --force to confirm.
    '''
    cmd = args[SUB_COMMAND]
    with db.session_context() as s:
        if cmd == NEW:
            new_kit(s, args[TYPE], args[ITEM], args[DATE], args[FORCE])
        elif cmd == ADD:
            add_kit(s, args[ITEM], args[COMPONENT], args[PART], args[DATE], args[FORCE])


def new_kit(s, type, item, date, force):
    type_instance = KitType.get(s, type, force)
    item_instance = KitItem.new(s, type_instance, item)
    log.info(f'Created {type_instance.name} {item_instance.name}')


def add_kit(s, item, component, part, date, force):
    item_instance = KitItem.get(s, item)
    component_instance = KitComponent.get(s, component, force)
    part_instance = KitPart.add(s, item_instance, component_instance, part, date, force)
    log.info(f'Added {item_instance.name} {component_instance.name} {part_instance.name} '
             f'at {time_to_local_time(part_instance.time_added(s))}')
