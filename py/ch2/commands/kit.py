from logging import getLogger
from sys import stdout

from .args import SUB_COMMAND, GROUP, ITEM, DATE, FORCE, COMPONENT, MODEL, NAME, SHOW, CSV, \
    START, CHANGE, FINISH, DELETE, UNDO, ALL, REBUILD, DUMP, KIT, CMD, VALUE, STATISTICS
from ..common.args import mm
from ..common.date import format_minutes
from ..diary.model import TYPE, UNITS
from ..lib import time_to_local_time, local_time_or_now, local_time_to_time, now, format_km, \
    is_local_time
from ..lib.tree import to_tree, to_csv
from ..names import U, N
from ..pipeline.calculate.kit import KitCalculator
from ..pipeline.pipeline import run_pipeline
from ..sql import PipelineType, Timestamp
from ..sql.tables.kit import KitGroup, KitItem, KitComponent, KitModel, get_name, ADDED, EXPIRED, _N, INDIVIDUAL, SUM
from ..sql.tables.source import Composite
from ..sql.types import long_cls, short_cls

log = getLogger(__name__)


def kit(config, output=stdout):
    '''
## kit

Track equipment, including the lifetime of particular components.

    > ch2 kit new GROUP ITEM
    > ch2 kit change ITEM COMPONENT MODEL
    > ch2 kit statistics ITEM

For full details see `ch2 kit -h` and `ch2 kit SUBCOMMAND -h`.

### Examples

Note that in practice some commands that do 'important' changes to the database require `--force` for confirmation.

    > ch2 kit start bike cotic
    > ch2 kit change cotic chain sram --start
    # ... some months later ...
    > ch2 kit change cotic chain kmc
    # ... more time later ...
    > ch2 kit change cotic chain sram
    > ch2 kit statistics chain

This example will give statistics on how long (time, distance) different bikes chains lasted.

In addition, when uploading activities, the `kit` variable must be defined.  So, for example:

    > ch2 upload --kit cotic **/*.fit

In this way the system knows what equipment was used in what activity.

Finally, statistics may be incorrect if the equipment is modified (because the correct use will not be
associated with each activity).  To recalculate use

    > ch2 kit rebuild

For running shoes you might simply track each item:

    > ch2 kit start shoe adidas
    # ... later ...
    > ch2 kit finish adidas
    > ch2 kit start shoe nike

Statistics for shoes:

    > ch2 kit statistic shoe

Names can be chosen at will (there is nothing hard-coded about 'bike', 'chain', 'cotic', etc),
but in general must be unique.  They can contain spaces if quoted.
    '''
    args = config.args
    cmd = args[SUB_COMMAND]
    with config.db.session_context() as s:
        if cmd == START:
            start(s, args[GROUP], args[ITEM], args[DATE], args[FORCE])
        elif cmd == FINISH:
            finish(s, args[ITEM], args[COMPONENT], args[DATE], args[FORCE])
        elif cmd == DELETE:
            delete(s, args[NAME], args[FORCE])
        elif cmd == CHANGE:
            change(s, args[ITEM], args[COMPONENT], args[MODEL], args[DATE], args[FORCE], args[START])
        elif cmd == UNDO:
            undo(s, args[ITEM], args[COMPONENT], args[MODEL], args[DATE], args[ALL])
        elif cmd == SHOW:
            show(s, args[NAME], args[DATE], csv=args[CSV], all=args[ALL], output=output)
        elif cmd == STATISTICS:
            statistics(s, args[NAME], csv=args[CSV], output=output)
        elif cmd == DUMP:
            dump(s, args[CMD])
        elif cmd == REBUILD:
            rebuild(s, config)


def start(s, group, item, date, force):
    date = local_time_or_now(date)
    group_instance = KitGroup.get_or_add(s, group, force=force)
    item_instance = KitItem.add(s, group_instance, item, date)
    log.info(f'Started {group_instance.name} {item_instance.name} '
             f'at {time_to_local_time(item_instance.time_added(s))}')


def finish(s, item, component, date, force):
    # complicated because component and date are both optional
    if component is None:  # date must be None too, since it comes second on command line
        date = now()
    elif date is None:
        if is_local_time(component):  # only one was supplied and it looks like a date
            component, date = None, local_time_to_time(component)
        else:
            date = now()
    else:
        date = local_time_to_time(date)
    if component and force:
        raise Exception(f'Cannot use {mm(FORCE)} with component (would change all models)')
    item = get_name(s, item, classes=(KitItem,), require=True)
    if component:
        component = get_name(s, component, classes=(KitComponent,), require=True)
        component.finish(s, item, date)
    else:
        item.finish(s, date, force)


def delete(s, name, force):
    s.expunge_all()
    instance = get_name(s, name, classes=(KitGroup, KitItem), require=True)
    if isinstance(instance, KitGroup) and not force:
        raise Exception(f'Specify {mm(FORCE)} to delete group')
    s.delete(instance)
    s.flush()
    for component in s.query(KitComponent).all():
        component.delete_if_unused(s)
    Composite.clean(s)


def change(s, item, component, model, date, force, start):
    item_instance = KitItem.get(s, item)
    if start:
        if date:
            raise Exception(f'Do not provide a date with {mm(START)}')
        date = item_instance.time_added(s)
    else:
        date = local_time_or_now(date)
    component_instance = KitComponent.get_or_add(s, component, force)
    model_instance = KitModel.add(s, item_instance, component_instance, model, date)
    log.info(f'Changed {item_instance.name} {component_instance.name} {model_instance.name} '
             f'at {time_to_local_time(model_instance.time_added(s))}')


def undo(s, item, component, model, date, all):
    item_instance = KitItem.get(s, item)
    component_instance = KitComponent.get(s, component)
    if all:
        if date:
            raise Exception(f'Provide date or {mm(ALL)}, not both')
        model_instance = KitModel.get(s, item_instance, component_instance, model, None)
        while model_instance:
            model_instance.undo(s)
            model_instance = KitModel.get(s, item_instance, component_instance, model, None, require=False)
    else:
        model_instance = KitModel.get(s, item_instance, component_instance, model, local_time_or_now(date))
        model_instance.undo(s)
    component_instance.delete_if_unused(s)


def rebuild(s, config):
    Timestamp.clear(s, owner=short_cls(KitCalculator))
    s.commit()
    run_pipeline(config, PipelineType.PROCESS, like=[long_cls(KitCalculator)])


def show(s, name, date, csv=None, all=False, output=stdout):
    # this is complicated because both name and date are optional so if only one is
    # supplied we need to guess which from the format.
    if name is None:  # date must be None too, since it comes second on command line
        name, time = '*', now()
    elif date is None:
        if is_local_time(name):  # only one was supplied and it looks like a date
            name, time = '*', local_time_to_time(name)
        else:
            time = now()
    else:
        time = local_time_to_time(date)
    if name == '*':
        models = [group.to_model(s, time=time, depth=3, statistics=INDIVIDUAL)
                  for group in s.query(KitGroup).order_by(KitGroup.name).all()]
    else:
        models = [get_name(s, name, classes=(KitGroup, KitItem), require=True)
                      .to_model(s, time=time, depth=3, statistics=INDIVIDUAL)]
    driver = to_csv if csv else to_tree
    format = to_stats_csv if csv else to_stats
    for model in models:
        for line in driver(model, format, model_children):
            print(line, file=output)


CHILDREN = {KitGroup.SIMPLE_NAME: N._s(KitItem.SIMPLE_NAME),
            KitItem.SIMPLE_NAME: N._s(KitComponent.SIMPLE_NAME),
            KitComponent.SIMPLE_NAME: N._s(KitModel.SIMPLE_NAME)}


def model_children(model):
    if TYPE in model and model[TYPE] in CHILDREN and CHILDREN[model[TYPE]] in model:
        log.debug(f'Traversing from {model[TYPE]} to {CHILDREN[model[TYPE]]}')
        yield from model[CHILDREN[model[TYPE]]]


def to_label_name_dates(model):
    if ADDED in model:
        return f'{model[TYPE]}: {model[NAME]}  {model[ADDED]} - {model[EXPIRED] or ""}', None
    else:
        return f'{model[TYPE]}: {model[NAME]}', None


def to_label_name_dates_csv(model):
    if ADDED in model:
        added = time_to_local_time(model[ADDED])
        expired = time_to_local_time(model[EXPIRED]) if model[EXPIRED] else ''
    else:
        added, expired = '', ''
    return f'{q(model[TYPE])},{q(model[NAME])},{q(added)},{q(expired)}', None


def statistics(s, name, csv=False, output=stdout):
    if name:
        models = [get_name(s, name, require=True).to_model(s, depth=3, statistics=INDIVIDUAL)]
    else:
        models = [group.to_model(s, depth=3, statistics=INDIVIDUAL)
                  for group in s.query(KitGroup).order_by(KitGroup.name).all()]
    driver = to_csv if csv else to_tree
    format = to_stats_csv if csv else to_stats
    log.debug(models)
    for model in models:
        for line in driver(model, format, model_children):
            print(line, file=output)


def stats_children(model):
    names = [key for key in model.keys() if key not in (NAME, UNITS)]
    return [{NAME: _N, VALUE: model[_N]}] + \
           [{NAME: name, VALUE: format_model(model)(model[name])} for name in names if name != _N]


def format_model(model):
    if model[UNITS] == U.KM:
        return format_km
    elif model[UNITS] == U.S:
        return lambda s: format_minutes(int(s))
    else:
        return lambda x: x


def to_stats(model):
    if TYPE in model:
        if ADDED in model:
            label = f'{model[TYPE]}: {model[NAME]}  {model[ADDED]} - {model[EXPIRED] or ""}'
        else:
            label = f'{model[TYPE]}: {model[NAME]}'
        if STATISTICS in model:
            log.debug(f'Extracting statistics from {model[TYPE]}')
            return label, model[STATISTICS]
        else:
            log.debug('No statistics in model')
            return label, None
    elif VALUE not in model:
        log.debug('Formatting statistic')
        return f'{model[NAME]}: {format_model(model)(model[SUM])}', None
        # return f'{model[NAME]}', stats_children(model)
    else:
        # leaf
        return f'{model[NAME]}: {model[VALUE]}', None


def to_stats_csv(model):
    if TYPE in model:
        label = f'{q(model[TYPE])},{q(model[NAME])}'
        if STATISTICS in model:
            return label, model[STATISTICS]
        else:
            return label, None
    elif VALUE not in model:
        return f'{q(model[NAME])}', stats_children(model)
    else:
        return f'{q(model[NAME])},{q(model[VALUE])}', None


def q(name):
    name = str(name)
    if ' ' in name:
        return f"'{name}'"
    else:
        return name


def qd(time):
    return q(time_to_local_time(time))


def dump(s, cmd):
    if cmd is None: cmd = 'ch2'
    print('#!/bin/sh')
    print('# script generated by')
    print(f'# > {cmd} {KIT} {DUMP} {mm(CMD)} {q(cmd)}')
    groups = s.query(KitGroup).order_by(KitGroup.name).all()
    for group in groups:
        delete_group(s, cmd, group)
    for group in groups:
        dump_group(s, cmd, group)
    print(f'{cmd} {KIT} {REBUILD}')


def delete_group(s, cmd, group):
    print(f'{cmd} {KIT} {DELETE} {mm(FORCE)} {q(group.name)}')


def dump_group(s, cmd, group):
    for item in s.query(KitItem).filter(KitItem.group == group).all():
        dump_item(s, cmd, item)


def dump_item(s, cmd, item):
    print(f'{cmd} {KIT} {START} {mm(FORCE)} {q(item.group.name)} {q(item.name)} {qd(item.time_added(s))}')
    for model in s.query(KitModel).filter(KitModel.item == item).all():
        dump_model(s, cmd, item, model)


def dump_model(s, cmd, item, model):
    print(f'{cmd} {KIT} {CHANGE} {mm(FORCE)} {q(item.name)} {q(model.component.name)} {q(model.name)} '
          f'{qd(model.time_added(s))}')

