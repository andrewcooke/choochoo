
from ..lib import log_current_exception
from ..config.database import add
from ..sql import Segment


def import_segment(record, old, new):
    if not segment_imported(record, new):
        try:
            with old.session_context() as old_s:
                with new.session_context() as new_s:
                    copy_segments(record, old_s, old, new_s)
        except Exception as e:
            log_current_exception()
            record.warning(f'Aborting segment import: {e}')


def segment_imported(record, new):
    with new.session_context() as new_s:
        return bool(new_s.query(Segment).count())


def copy_segments(record, old_s, old, new_s):
    segment = old.meta.tables['segment']
    for old_segment in old_s.query(segment).all():
        add(new_s, Segment(name=old_segment.name, description=old_segment.description,
                           distance=old_segment.distance,
                           start_lat=old_segment.start_lat, start_lon=old_segment.start_lon,
                           finish_lat=old_segment.finish_lat, finish_lon=old_segment.finish_lon))
        record.info(f'Segment {old_segment.name}')
