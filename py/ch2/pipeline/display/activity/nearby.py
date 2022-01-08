
from sqlalchemy import or_, desc, asc
from sqlalchemy.orm import aliased

from ..utils import ActivityJournalDelegate
from ....common.date import to_time, time_to_local_time
from ....diary.model import text, link, optional_text
from ....sql import ActivityJournal, ActivityDistance
from ....sql.support import greatest

NEARBY_LINKS = 'nearby-links'


def fmt_nearby(aj, nb):
    return to_time(aj.start).strftime('%y-%m-%d') + ' %dkm' % (nb.distance / 1000)


class NearbyDelegate(ActivityJournalDelegate):

    @optional_text('Nearby', tag='nearby')
    def read_journal_date(self, s, ajournal, date):
        yield from self.__read_nearby(s, ajournal)

    def __read_nearby(self, s, ajournal):
        for title, callback in (('Any Time', nearby_any_time), ('Earlier', nearby_earlier)):
            links = [link(fmt_nearby(aj, nb), db=(time_to_local_time(aj.start),))
                     for (aj, nb) in callback(s, ajournal)]
            if links:
                yield [text(title, tag=NEARBY_LINKS)] + links

    def read_interval(self, s, interval):
        return
        yield


def nearby_earlier(s, ajournal, threshold=10000):
    aj_lo = aliased(ActivityJournal)
    aj_hi = aliased(ActivityJournal)
    q = s.query(ActivityDistance). \
        join(aj_hi, ActivityDistance.activity_journal_hi_id == aj_hi.id). \
        join(aj_lo, ActivityDistance.activity_journal_lo_id == aj_lo.id). \
        filter(or_(ActivityDistance.activity_journal_hi_id == ajournal.id,
                   ActivityDistance.activity_journal_lo_id == ajournal.id),
               aj_lo.activity_group_id == aj_hi.activity_group_id,
               or_(aj_hi.id == ajournal.id, aj_hi.start < ajournal.start),
               or_(aj_hi.id == ajournal.id, aj_lo.start < ajournal.start),
               ActivityDistance.distance < threshold). \
        order_by(desc(greatest(aj_lo.start, aj_hi.start)))
    return [(asm.activity_journal_lo if asm.activity_journal_lo != ajournal else asm.activity_journal_hi, asm)
            for asm in q.all()]


def nearby_any_time(s, ajournal, threshold=10000):
    aj_lo = aliased(ActivityJournal)
    aj_hi = aliased(ActivityJournal)
    q = s.query(ActivityDistance). \
        join(aj_hi, ActivityDistance.activity_journal_hi_id == aj_hi.id). \
        join(aj_lo, ActivityDistance.activity_journal_lo_id == aj_lo.id). \
        filter(or_(ActivityDistance.activity_journal_hi_id == ajournal.id,
                   ActivityDistance.activity_journal_lo_id == ajournal.id),
               aj_lo.activity_group_id == aj_hi.activity_group_id,
               ActivityDistance.distance < threshold). \
        order_by(asc(ActivityDistance.distance))
    return [(asm.activity_journal_lo if asm.activity_journal_lo != ajournal else asm.activity_journal_hi, asm)
            for asm in q.all()]
