
from logging import getLogger
from sys import stdout

from sqlalchemy import alias, or_
from sqlalchemy.orm import aliased

from ch2.stoats.names import KIT_ADDED, KIT_RETIRED
from ..squeal.tables.statistic import StatisticJournalTimestamp, StatisticName
from .args import SUB_COMMAND, NEW, GROUP, ITEM, DATE, FORCE, ADD, COMPONENT, MODEL, STATISTICS, NAME, SHOW
from ..lib import time_to_local_time, local_time_or_now, local_time_to_time, now
from ..squeal.tables.kit import KitGroup, KitItem, KitComponent, KitModel, find_name

log = getLogger(__name__)


def kit(args, db, output=stdout):
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
        elif cmd == SHOW:
            show(s, args[ITEM], args[DATE], output=output)
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


def show(s, item, date, output=stdout):
    instance = s.query(KitItem).filter(KitItem.name == item).one_or_none()
    if instance:
        item = instance
        date = local_time_or_now(date)
    else:
        if item:
            if date:
                raise Exception(f'Cannot find {item}')
            else:
                try:
                    date = local_time_to_time(item)
                    item = None
                except:
                    raise Exception(f'Cannot parse {item} as a date')
        else:
            date = now()
    if item:
        show_item(s, item, date)
    else:
        for item in s.query(KitItem).order_by(KitItem.name).all():
            show_item(s, item, date, output=output)


def show_item(s, item, date, output=stdout):
    log.debug(f'{item} {date}')
    print(f'{item.name}', file=output)
    ts_before, sn_before = aliased(StatisticJournalTimestamp), aliased(StatisticName)
    ts_after, sn_after = aliased(StatisticJournalTimestamp), aliased(StatisticName)
    q = s.query(KitModel).\
            join(sn_before, sn_before.constraint == item).join(ts_before, ts_before.statistic_name_id == sn_before.id).\
            outerjoin(sn_after, sn_after.constraint == item).join(ts_after, ts_after.statistic_name_id == sn_after.id).\
            filter(KitModel.item == item,
                   sn_before.name == KIT_ADDED,
                   sn_after.name == KIT_RETIRED,
                   ts_before.time <= date,
                   or_(ts_after.time >= date, ts_after.time == None))
    log.debug(q)
    for model in q.all():
        log.debug(model)


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
