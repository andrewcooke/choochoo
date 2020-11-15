
from logging import getLogger

from geoalchemy2 import WKTElement, WKBElement
from geoalchemy2.shape import to_shape
from sqlalchemy import text

from ..utils import ActivityJournalDelegate
from ....diary.model import optional_text, map
from ....sql.utils import SPHM_SRID

log = getLogger(__name__)


class MapDelegate(ActivityJournalDelegate):

    @optional_text('Map')
    def read_journal_date(self, s, ajournal, date):
        q = text(f'''
select st_envelope(st_transform(aj.route_t::geometry, {SPHM_SRID}))
  from activity_journal as aj
 where aj.id = :activity_journal_id
''')
        row = s.connection().execute(q, activity_journal_id=ajournal.id).fetchone()
        envelope = to_shape(WKBElement(row[0]))
        yield map(envelope.bounds, ('activity', str(ajournal.id)))

    def read_interval(self, s, interval):
        # todo?
        return
        yield
