
from itertools import groupby
from logging import getLogger
from sys import stdout

from numpy import median
from sqlalchemy import or_

from .args import SUB_COMMAND, NEW, GROUP, ITEM, DATE, FORCE, ADD, COMPONENT, MODEL, STATISTICS, NAME, SHOW, CSV
from ..lib import time_to_local_time, local_time_or_now, local_time_to_time, now, format_seconds, format_metres
from ..squeal.tables.kit import KitGroup, KitItem, KitComponent, KitModel, get_name
from ..squeal.tables.statistic import StatisticJournalTimestamp, StatisticName
from ..stoats.names import KIT_ADDED, KIT_RETIRED, ACTIVE_TIME, ACTIVE_DISTANCE

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
            show(s, args[ITEM], args[DATE]).display(csv=args[CSV], output=output)
        elif cmd == STATISTICS:
            statistics(s, args[NAME]).display(csv=args[CSV], output=output)


def new(s, group, item, date, force):
    group_instance = KitGroup.get(s, group, force=force)
    item_instance = KitItem.new(s, group_instance, item, date)
    log.info(f'Created {group_instance.name} {item_instance.name}'
             f'at {time_to_local_time(item_instance.time_added(s))}')


def add(s, item, component, part, date, force):
    item_instance = KitItem.get(s, item)
    component_instance = KitComponent.get(s, component, force)
    model_instance = KitModel.add(s, item_instance, component_instance, part, date, force)
    log.info(f'Added {item_instance.name} {component_instance.name} {model_instance.name} '
             f'at {time_to_local_time(model_instance.time_added(s))}')


def show(s, item, date, csv=False, output=stdout):
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
        return show_item(s, item, date)
    else:
        return Node('All items', (show_item(s, item, date)
                                  for item in s.query(KitItem).order_by(KitItem.name).all()))


def show_item(s, item, date):
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
    instance = get_name(s, name)
    return {KitGroup: group_statistics,
            KitItem: item_statistics,
            KitComponent: component_statistics,
            KitModel: model_statistics}[type(instance)](s, instance)


def stats_node(title, values, fmt):
    n = len(values)
    total = sum(values)
    avg = total / n
    med = median(values)
    return Node(title,
                (Leaf(f'Count {n}'),
                 Leaf(f'Sum {fmt(total)}'),
                 Leaf(f'Average {fmt(avg)}'),
                 Leaf(f'Median {fmt(med)}')))


def group_statistics(s, group, output=stdout):
    return Node(f'Group {group.name}',
                (stats_node('Lifetime',
                            [item.lifetime(s).total_seconds() for item in group.items],
                            format_seconds),
                 stats_node(ACTIVE_TIME,
                            [sum(time.value for time in item.active_times(s)) for item in group.items],
                            format_seconds),
                 stats_node(ACTIVE_DISTANCE,
                            [sum(distance.value for distance in item.active_distances(s)) for item in group.items],
                            format_metres)))


def item_statistics(s, item, output=stdout):
    components = item.components
    ordered_components = sorted(components.keys(), key=lambda component: component.name)
    return Node(f'Item {item.name}',
                [Leaf(f'Lifetime {format_seconds(item.lifetime(s).total_seconds())}'),
                 stats_node(ACTIVE_TIME,
                            [time.value for time in item.active_times(s)],
                            format_seconds),
                 stats_node(ACTIVE_DISTANCE,
                            [distance.value for distance in item.active_distances(s)],
                            format_metres)]
                +
                [Node(f'Component {component.name}',
                      (stats_node('Lifetime',
                                  [model.lifetime(s).total_seconds() for model in components[component]],
                                  format_seconds),
                       stats_node(ACTIVE_TIME,
                                  [sum(time.value for time in model.active_times(s)) for model in components[component]],
                                  format_seconds),
                       stats_node(ACTIVE_DISTANCE,
                                  [sum(time.value for time in model.active_distances(s)) for model in components[component]],
                                  format_metres)))
                 for component in ordered_components])


def component_statistics(s, component, output=stdout):
    log.info('component')


def model_statistics(s, model, output=stdout):
    log.info('model')


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


class Leaf:

    def __init__(self, value):
        self.value = value

    def csv(self, line='', output=stdout):
        print(line + self.value, file=output)

    def tree_lines(self):
        yield self.value
