from logging import getLogger

from ..lib import log_current_exception
from ..config.database import add
from ..sql import Segment

log = getLogger(__name__)


def import_segment(record, old, new):
    if not segment_imported(record, new):
        record.info('Importing segment entries')
        try:
            with old.session_context() as old_s:
                with new.session_context() as new_s:
                    copy_segments(record, old_s, old, new_s)
        except Exception as e:
            log_current_exception()
            record.warning(f'Aborting segment import: {e}')
    else:
        record.warning('Segment entries already imported')


def segment_imported(record, new):
    with new.session_context() as new_s:
        return bool(new_s.query(Segment).count())


def copy_segments(record, old_s, old, new_s):
    segment = old.meta.tables['segment']
    for old_segment in old_s.query(segment).all():
        title = old_segment.name if hasattr(old_segment, 'name') else old_segment.title
        add(new_s, Segment(title=title, description=old_segment.description,
                           distance=old_segment.distance,
                           start_lat=old_segment.start_lat, start_lon=old_segment.start_lon,
                           finish_lat=old_segment.finish_lat, finish_lon=old_segment.finish_lon))
        record.info(f'Segment {title}')
