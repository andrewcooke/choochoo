
from sqlalchemy import or_, desc, distinct
from sqlalchemy.orm import aliased
from sqlalchemy.sql.functions import min

from ..utils import ActivityJournalDelegate
from ....diary.model import text, link, optional_text
from ....lib.date import to_time, time_to_local_time
from ....sql import ActivityJournal, ActivitySimilarity, ActivityNearby

NEARBY_LINKS = 'nearby-links'


def fmt_nearby(aj, nb):
    return to_time(aj.start).strftime('%y-%m-%d') + ' %d%%' % (nb.similarity * 100)


class NearbyDelegate(ActivityJournalDelegate):

    def read_schedule(self, s, date, schedule):
        yield from []

    @optional_text('Nearby', tag='nearby')
    def read_journal_date(self, s, ajournal, date):
        yield from self.__read_nearby(s, ajournal)

    def __read_nearby(self, s, ajournal):
        for title, callback in (('Any Time', nearby_any_time), ('Earlier', nearby_earlier)):
            links = [link(fmt_nearby(aj, nb), db=(time_to_local_time(aj.start),))
                     for (aj, nb) in callback(s, ajournal)]
            if links:
                yield [text(title, tag=NEARBY_LINKS)] + links


def nearby_earlier(s, ajournal, threshold=0.3):
    aj_lo = aliased(ActivityJournal)
    aj_hi = aliased(ActivityJournal)
    q = s.query(ActivitySimilarity). \
        join(aj_hi, ActivitySimilarity.activity_journal_hi_id == aj_hi.id). \
        join(aj_lo, ActivitySimilarity.activity_journal_lo_id == aj_lo.id). \
        filter(or_(ActivitySimilarity.activity_journal_hi_id == ajournal.id,
                   ActivitySimilarity.activity_journal_lo_id == ajournal.id),
               aj_lo.activity_group_id == aj_hi.activity_group_id,
               or_(aj_hi.id == ajournal.id, aj_hi.start < ajournal.start),
               or_(aj_hi.id == ajournal.id, aj_lo.start < ajournal.start),
               ActivitySimilarity.similarity > threshold). \
        order_by(desc(min(aj_lo.start, aj_hi.start)))
    return [(asm.activity_journal_lo if asm.activity_journal_lo != ajournal else asm.activity_journal_hi, asm)
            for asm in q.all()]


def nearby_any_time(s, ajournal, threshold=0.3):
    aj_lo = aliased(ActivityJournal)
    aj_hi = aliased(ActivityJournal)
    q = s.query(ActivitySimilarity). \
        join(aj_hi, ActivitySimilarity.activity_journal_hi_id == aj_hi.id). \
        join(aj_lo, ActivitySimilarity.activity_journal_lo_id == aj_lo.id). \
        filter(or_(ActivitySimilarity.activity_journal_hi_id == ajournal.id,
                   ActivitySimilarity.activity_journal_lo_id == ajournal.id),
               aj_lo.activity_group_id == aj_hi.activity_group_id,
               ActivitySimilarity.similarity > threshold). \
        order_by(desc(ActivitySimilarity.similarity))
    return [(asm.activity_journal_lo if asm.activity_journal_lo != ajournal else asm.activity_journal_hi, asm)
            for asm in q.all()]
