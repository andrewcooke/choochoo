
from itertools import groupby
from logging import getLogger
from sys import stdout

from numpy import median
from sqlalchemy import or_

from .args import SUB_COMMAND, GROUP, ITEM, DATE, FORCE, COMPONENT, MODEL, STATISTICS, NAME, SHOW, CSV, \
    START, CHANGE, FINISH, DELETE, mm, UNDO, ALL
from ..lib import time_to_local_time, local_time_or_now, local_time_to_time, now, format_seconds, format_metres, \
    groupby_tuple
from ..squeal.tables.kit import KitGroup, KitItem, KitComponent, KitModel, get_name
from ..squeal.tables.statistic import StatisticJournalTimestamp, StatisticName
from ..squeal.tables.source import Composite
from ..stoats.names import KIT_ADDED, KIT_RETIRED, ACTIVE_TIME, ACTIVE_DISTANCE, LIFETIME

log = getLogger(__name__)


def kit(args, db, output=stdout):
    '''
## kit

    '''
    cmd = args[SUB_COMMAND]
    with db.session_context() as s:
        if cmd == START:
            start(s, args[GROUP], args[ITEM], args[DATE], args[FORCE])
        elif cmd == FINISH:
            finish(s, args[ITEM], args[DATE], args[FORCE])
        elif cmd == DELETE:
            delete(s, args[NAME], args[FORCE])
        elif cmd == CHANGE:
            change(s, args[ITEM], args[COMPONENT], args[MODEL], args[DATE], args[FORCE])
        elif cmd == UNDO:
            undo(s, args[ITEM], args[COMPONENT], args[MODEL], args[DATE], args[ALL])
        elif cmd == SHOW:
            show(s, args[ITEM], args[DATE]).display(csv=args[CSV], output=output)
        elif cmd == STATISTICS:
            statistics(s, args[NAME]).display(csv=args[CSV], output=output)


def start(s, group, item, date, force):
    group_instance = KitGroup.get_or_add(s, group, force=force)
    item_instance = KitItem.add(s, group_instance, item, date)
    log.info(f'Started {group_instance.name} {item_instance.name} '
             f'at {time_to_local_time(item_instance.time_added(s))}')


def finish(s, item, date, force):
    get_name(s, item, classes=(KitItem,), require=True).finish(s, date, force)
    log.info(f'Finished {item}')


def delete(s, name, force):
    instance = get_name(s, name, classes=(KitGroup, KitItem), require=True)
    if isinstance(instance, KitGroup) and not force:
        raise Exception(f'Specify {mm(FORCE)} to delete group')
    s.delete(instance)
    Composite.clean(s)


def change(s, item, component, model, date, force):
    item_instance = KitItem.get(s, item)
    component_instance = KitComponent.get_or_add(s, component, force)
    model_instance = KitModel.add(s, item_instance, component_instance, model, date)
    log.info(f'Changed {item_instance.name} {component_instance.name} {model_instance.name} '
             f'at {time_to_local_time(model_instance.time_added(s))}')


def undo(s, item, component, model, date, all):
    item_instance = KitItem.get(s, item)
    component_instance = KitComponent.get(s, component)


def show(s, item, date):
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
                    raise Exception(f'Cannot parse {item} as a date (and it is not an item)')
        else:
            date = now()
    if item:
        return show_item(s, item, date)
    else:
        return Node('All items', (show_item(s, item, date)
                                  for item in s.query(KitItem).order_by(KitItem.name).all()))


def show_item(s, item, date):
    # todo - include start dates so they can be used for undo
    beforeq = s.query(StatisticJournalTimestamp.source_id, StatisticJournalTimestamp.time). \
        join(StatisticName). \
        filter(StatisticName.name == KIT_ADDED).subquery()
    afterq = s.query(StatisticJournalTimestamp.source_id, StatisticJournalTimestamp.time). \
        join(StatisticName). \
        filter(StatisticName.name == KIT_RETIRED).subquery()
    models = s.query(KitModel). \
        join(beforeq, beforeq.c.source_id == KitModel.id). \
        outerjoin(afterq, afterq.c.source_id == KitModel.id). \
        filter(KitModel.item == item,
               beforeq.c.time <= date,
               or_(afterq.c.time >= date, afterq.c.time == None)).all()
    return Node(f'Item {item.name}',
                (Node(f'Component {component}',
                      (Leaf(f'Model {model.name}') for model in models))
                 for component, models in groupby(models, key=lambda m: m.component.name)))


def statistics(s, name):
    instance = get_name(s, name, require=True)
    return {KitGroup: group_statistics,
            KitItem: item_statistics,
            KitComponent: component_statistics,
            KitModel: model_statistics}[type(instance)](s, instance)


def stats(title, values, fmt):
    n = len(values)
    if n == 0:
        return Leaf(f'{title} [no data]')
    elif n == 1:
        return Leaf(f'{title} {fmt(values[0])}')
    else:
        total = sum(values)
        avg = total / n
        med = median(values)
        return Node(title,
                    (Leaf(f'Count {n}'),
                     Leaf(f'Sum {fmt(total)}'),
                     Leaf(f'Average {fmt(avg)}'),
                     Leaf(f'Median {fmt(med)}')))


def group_statistics(s, group):
    return Node(f'Group {group.name}',
                (stats(LIFETIME,
                       [item.lifetime(s).total_seconds() for item in group.items],
                       format_seconds),
                 stats(ACTIVE_TIME,
                       [sum(time.value for time in item.active_times(s)) for item in group.items],
                       format_seconds),
                 stats(ACTIVE_DISTANCE,
                       [sum(distance.value for distance in item.active_distances(s)) for item in group.items],
                       format_metres)))


def item_statistics(s, item):
    components = item.components
    ordered_components = sorted(components.keys(), key=lambda component: component.name)
    return Node(f'Item {item.name}',
                [Leaf(f'{LIFETIME} {format_seconds(item.lifetime(s).total_seconds())}'),
                 stats(ACTIVE_TIME,
                       [time.value for time in item.active_times(s)],
                       format_seconds),
                 stats(ACTIVE_DISTANCE,
                       [distance.value for distance in item.active_distances(s)],
                       format_metres)]
                +
                [Node(f'Component {component.name}',
                      (stats(LIFETIME,
                             [model.lifetime(s).total_seconds() for model in components[component]],
                             format_seconds),
                       stats(ACTIVE_TIME,
                             [sum(time.value for time in model.active_times(s)) for model in components[component]],
                             format_seconds),
                       stats(ACTIVE_DISTANCE,
                             [sum(time.value for time in model.active_distances(s)) for model in components[component]],
                             format_metres)))
                 for component in ordered_components])


def component_statistics(s, component, output=stdout):
    return Node(f'Item {component.name}',
                [Node(f'Model {name}',
                      (stats(LIFETIME,
                             [model.lifetime(s).total_seconds() for model in group],
                             format_seconds),
                       stats(ACTIVE_TIME,
                             [sum(time.value for time in model.active_times(s)) for model in group],
                             format_seconds),
                       stats(ACTIVE_DISTANCE,
                             [sum(time.value for time in model.active_distances(s)) for model in group],
                             format_metres)))
                 for name, group in groupby_tuple(sorted(component.models, key=lambda model: model.name),
                                                  key=lambda model: model.name)])
    # todo - order by active distance?


def model_statistics(s, model):
    models = s.query(KitModel).filter(KitModel.name == model.name).all()
    return Node(f'Model {model.name}',
                (stats(LIFETIME,
                       [model.lifetime(s).total_seconds() for model in models],
                       format_seconds),
                 stats(ACTIVE_TIME,
                       [sum(time.value for time in model.active_times(s)) for model in models],
                       format_seconds),
                 stats(ACTIVE_DISTANCE,
                       [sum(time.value for time in model.active_distances(s)) for model in models],
                       format_metres)))


class Node:

    def __init__(self, label, children):
        self.label = label
        self.children = tuple(children)

    def display(self, csv=False, output=stdout):
        if csv:
            self.csv(output=output)
        else:
            self.tree(output=output)

    def csv(self, line='', output=stdout):
        for child in self.children:
            child.csv(line + f'{self.label},', output=output)

    def tree(self, output=stdout):
        print('\n'.join(self.tree_lines()), file=output)

    def tree_lines(self):
        yield self.label
        last = self.children[-1] if self.children else None
        for child in self.children:
            prefix = '`-' if child is last else '+-'
            for line in child.tree_lines():
                yield prefix + line
                prefix = '  ' if child is last else '| '

    def __len__(self):
        return 1 + sum(len(child) for child in self.children)


class Leaf:

    def __init__(self, value):
        self.value = value

    def csv(self, line='', output=stdout):
        print(line + self.value, file=output)

    def tree_lines(self):
        yield self.value

    def __len__(self):
        return 1
