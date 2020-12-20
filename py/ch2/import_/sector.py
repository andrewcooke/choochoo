from ..common.log import log_current_exception
from ..sql import Sector, SectorGroup
from ..sql.types import short_cls
from ..sql.utils import add
from ..web.servlets.sector import UserDefined


def import_sector(record, old, new):
    if not sector_imported(record, new):
        record.info('Importing sector entries')
        try:
            with old.session_context() as old_s:
                with new.session_context() as new_s:
                    groups = copy_sector_group(record, old_s, old, new_s)
                    copy_sector(record, old_s, old, new_s, groups)
        except Exception as e:
            log_current_exception()
            record.warning(f'Aborting sector import: {e}')
    else:
        record.warning('Sector entries already imported')


def sector_imported(record, new):
    with new.session_context() as new_s:
        return bool(new_s.query(Sector).count())


def copy_sector_group(record, old_s, old, new_s):
    groups = {}
    sector_group = old.meta.tables['sector_group']
    for old_sector_group in old_s.query(sector_group).all():
        new_sector_group = match_sector_group(new_s, old_sector_group)
        if new_sector_group:
            groups[new_sector_group.title] = new_sector_group
        else:
            groups[new_sector_group.title] = \
                add(new_s, SectorGroup(srid=old_sector_group.srid, centre=old_sector_group.centre,
                                       radius=old_sector_group.radius, title=old_sector_group.title))
            record.info(f'Sector Group {old_sector_group.title}')
    return groups


def match_sector_group(new_s, old_sector_group):
    # we could do a bunch of things here, but this is sufficient to avoid the worst errors
    return new_s.query(SectorGroup). \
        filter(SectorGroup.title == old_sector_group.title,
               SectorGroup.srid == old_sector_group.srid).one_or_none()


def copy_sector(record, old_s, old, new_s, groups):
    sector = old.meta.tables['sector']
    sector_group = old.meta.tables['sector_group']
    for old_sector in old_s.query(sector).filter(sector.c.owner == short_cls(UserDefined)).all():
        old_sector_group = old_s.query(sector_group).filter(sector_group.c.id == old_sector.sector_group_id).one()
        new_sector_group = groups[old_sector_group.title]
        add(new_s, Sector(sector_group_id=new_sector_group.id, route=old_sector.route, title=old_sector.title,
                          owner=UserDefined, distance=old_sector.distance,
                          start=old_sector.start, finish=old_sector.finish, hull=old_sector.hull))
        record.info(f'Sector {old_sector.title}')
