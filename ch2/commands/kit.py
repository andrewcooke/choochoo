
from logging import getLogger

from ..squeal.tables.kit import KitType, KitItem
from .args import SUB_COMMAND, NEW, TYPE, ITEM, DATE, FORCE

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


def new_kit(s, type, item, date, force):
    log.debug(f'{type} {item} {date}')
    type_instance = KitType.get(s, type, force)
    item_instance = KitItem.new(s, type_instance, item)
    log.info(f'Created {type_instance.name} {item_instance.name}')
