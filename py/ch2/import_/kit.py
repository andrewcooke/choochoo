
from logging import getLogger

from ..lib import format_date, time_to_local_date, to_time
from ..common.log import log_current_exception
from ..names import Titles, simple_name
from ..sql import KitGroup, KitComponent, KitItem, KitModel, StatisticJournalTimestamp, StatisticName, \
    StatisticJournalType
from ..sql.utils import add

log = getLogger(__name__)


def import_kit(record, old, new):
    if not kit_imported(record, new):
        record.info('Importing kit entries')
        try:
            with old.session_context() as old_s:
                with new.session_context() as new_s:
                    copy_components(record, old_s, old, new_s)
                    copy_tree(record, old_s, old, new_s)
        except Exception as e:
            log_current_exception()
            record.warning(f'Aborting kit import: {e}')
    else:
        record.warning('Kit entries already imported')


def kit_imported(record, new):
    with new.session_context() as new_s:
        return bool(new_s.query(KitGroup).count() + new_s.query(KitComponent).count())


def copy_components(record, old_s, old, new_s):
    component = old.meta.tables['kit_component']
    for old_component in old_s.query(component).all():
        add(new_s, KitComponent(name=old_component.name))
        record.info(f'Component {old_component.name}')


def copy_tree(record, old_s, old, new_s):
    group = old.meta.tables['kit_group']
    for old_group in old_s.query(group).all():
        new_group = add(new_s, KitGroup(name=old_group.name))
        record.info(f'Group {old_group.name}')
        item = old.meta.tables['kit_item']
        for old_item in old_s.query(item).filter(item.c.group_id == old_group.id).all():
            new_item = add(new_s, KitItem(name=old_item.name, group=new_group))
            record.info(f'Item {old_item.name}')
            copy_statistics(record, old_s, old, old_item, new_s, new_item)
            model = old.meta.tables['kit_model']
            component = old.meta.tables['kit_component']
            for old_model in old_s.query(model).filter(model.c.item_id == old_item.id).all():
                old_component = old_s.query(component).filter(component.c.id == old_model.component_id).one()
                new_component = new_s.query(KitComponent).filter(KitComponent.name == old_component.name).one()
                new_model = add(new_s, KitModel(name=old_model.name, item=new_item, component=new_component))
                record.info(f'Model {old_model.name}')
                copy_statistics(record, old_s, old, old_model, new_s, new_model)


def copy_statistics(record, old_s, old, old_source, new_s, new_source):
    statistic_name = old.meta.tables['statistic_name']
    statistic_journal = old.meta.tables['statistic_journal']
    statistic_journal_timestamp = old.meta.tables['statistic_journal_timestamp']
    for title in (Titles.KIT_ADDED, Titles.KIT_RETIRED):
        old_timestamp = old_s.query(statistic_journal). \
            join(statistic_journal_timestamp). \
            join(statistic_name). \
            filter(statistic_name.c.name.ilike(simple_name(title)),
                   statistic_journal.c.source_id == old_source.id).one_or_none()
        if old_timestamp:
            new_statistic_name = StatisticName.add_if_missing(new_s, title, StatisticJournalType.TIMESTAMP,
                                                              None, None, type(new_source))
            # to_time for sqlite
            add(new_s, StatisticJournalTimestamp(source=new_source, time=to_time(old_timestamp.time),
                                                 statistic_name=new_statistic_name))
            date = format_date(time_to_local_date(to_time(old_timestamp.time)))
            record.info(f'Statistic matching {title} at {date} for {old_source.name}')
