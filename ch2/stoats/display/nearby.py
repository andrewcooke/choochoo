
from sqlalchemy import or_, desc, distinct
from sqlalchemy.orm import aliased
from sqlalchemy.sql.functions import min
from urwid import Pile, Text

from . import JournalDiary
from ...lib.date import to_time
from ...lib.utils import label
from ...squeal import ActivityJournal
from ...squeal import ActivitySimilarity
from ...uweird.tui.decorators import Indent


def fmt(time):
    return to_time(time).strftime('%Y-%m-%d')


class NearbyDiary(JournalDiary):

    def _build_schedule(self, s, f, date, schedule=None):
        yield from []

    def _journal_date(self, s, ajournal, date):
        for constraint in [c[0] for c in
                           s.query(distinct(ActivitySimilarity.constraint)).
                                   order_by(ActivitySimilarity.constraint).all()]:
            rows = []
            rows += self._any_time(s, ajournal, constraint)
            rows += self._earlier(s, ajournal, constraint)
            if rows:
                yield Pile([Text(constraint),
                            Indent(Pile(rows))])

    def _any_time(self, s, ajournal, constraint):
        data = [aj.activity_journal_lo.start
                if aj.activity_journal_lo != ajournal
                else aj.activity_journal_hi.start
                for aj in s.query(ActivitySimilarity).
                    filter(or_(ActivitySimilarity.activity_journal_hi_id == ajournal.id,
                               ActivitySimilarity.activity_journal_lo_id == ajournal.id),
                           ActivitySimilarity.constraint == constraint,
                           ActivitySimilarity.similarity > 0.05).
                    order_by(desc(ActivitySimilarity.similarity)).limit(6).all()]
        if data:
            yield Text([label('Any Time: '), ' '.join(fmt(d) for d in data)])

    def _earlier(self, s, ajournal, constraint):
        ajlo = aliased(ActivityJournal)
        ajhi = aliased(ActivityJournal)
        data = [x[0] for x in
                s.query(min(ajlo.start, ajhi.start)).
                    select_from(ActivitySimilarity).
                    join(ajhi, ActivitySimilarity.activity_journal_hi_id == ajhi.id).
                    join(ajlo, ActivitySimilarity.activity_journal_lo_id == ajlo.id).
                    filter(or_(ActivitySimilarity.activity_journal_hi_id == ajournal.id,
                               ActivitySimilarity.activity_journal_lo_id == ajournal.id),
                           ActivitySimilarity.constraint == constraint,
                           or_(ajhi.id == ajournal.id, ajhi.start < ajournal.start),
                           or_(ajhi.id == ajournal.id, ajlo.start < ajournal.start),
                           ActivitySimilarity.similarity > 0.05).
                    order_by(desc(min(ajlo.start, ajhi.start))).limit(6).all()]
        if data:
            yield Text([label('Recent: '), ' '.join(fmt(d) for d in data)])
