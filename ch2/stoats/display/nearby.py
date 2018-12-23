
from sqlalchemy import or_, desc, distinct
from sqlalchemy.orm import aliased
from sqlalchemy.sql.functions import min
from urwid import Pile, Text, Columns

from . import JournalDiary
from ...lib.date import to_time, time_to_local_date
from ...lib.utils import label
from ...squeal import ActivityJournal
from ...squeal import ActivitySimilarity
from ...uweird.tui.decorators import Indent
from ...uweird.tui.widgets import SquareButton, ColSpace, ColText


def fmt(time):
    return to_time(time).strftime('%Y-%m-%d')


class NearbyDiary(JournalDiary):

    def _display_schedule(self, s, f, date, schedule=None):
        yield from []

    def _journal_date(self, s, f, ajournal, date):
        for constraint in [c[0] for c in
                           s.query(distinct(ActivitySimilarity.constraint)).
                                   order_by(ActivitySimilarity.constraint).all()]:
            rows = []
            rows += self._any_time(s, f, ajournal, constraint)
            rows += self._earlier(s, f, ajournal, constraint)
            if rows:
                yield Pile([Text(constraint),
                            Indent(Pile(rows))])

    def _on_press(self, w, time):
        self._diary._change_date(time_to_local_date(time))

    def _buttons(self, f, title, data):
        if data:
            btns = [(len(fmt(d.start)) + 2,
                     f(SquareButton(fmt(d.start), on_press=self._on_press, user_data=d.start))) for d in data]
            yield Columns([ColText('%s: ' % title, label), *btns, ColSpace()])

    def _any_time(self, s, f, ajournal, constraint):
        yield from self._buttons(f, 'Any Time', nearby_any_time(s, ajournal, constraint=constraint))

    def _earlier(self, s, f, ajournal, constraint):
        yield from self._buttons(f, 'Earlier', nearby_earlier(s, ajournal, constraint=constraint))


def single_constraint(s, ajournal):
    return s.query(distinct(ActivitySimilarity.constraint)). \
        filter(or_(ActivitySimilarity.activity_journal_lo_id == ajournal.id,
                   ActivitySimilarity.activity_journal_hi_id == ajournal.id)).scalar()


def nearby_earlier(s, ajournal, constraint=None, threshold=0.05):
    if constraint is None:
        constraint = single_constraint(s, ajournal)
    ajlo = aliased(ActivityJournal)
    ajhi = aliased(ActivityJournal)
    return [asm.activity_journal_lo
            if asm.activity_journal_lo != ajournal
            else asm.activity_journal_hi
            for asm in s.query(ActivitySimilarity).
                join(ajhi, ActivitySimilarity.activity_journal_hi_id == ajhi.id).
                join(ajlo, ActivitySimilarity.activity_journal_lo_id == ajlo.id).
                filter(or_(ActivitySimilarity.activity_journal_hi_id == ajournal.id,
                           ActivitySimilarity.activity_journal_lo_id == ajournal.id),
                       ActivitySimilarity.constraint == constraint,
                       or_(ajhi.id == ajournal.id, ajhi.start < ajournal.start),
                       or_(ajhi.id == ajournal.id, ajlo.start < ajournal.start),
                       ActivitySimilarity.similarity > threshold).
                order_by(desc(min(ajlo.start, ajhi.start))).limit(6).all()]


def nearby_any_time(s, ajournal, constraint=None, threshold=0.05):
    if constraint is None:
        constraint = single_constraint(s, ajournal)
    return [asm.activity_journal_lo
            if asm.activity_journal_lo != ajournal
            else asm.activity_journal_hi
            for asm in s.query(ActivitySimilarity).
                filter(or_(ActivitySimilarity.activity_journal_hi_id == ajournal.id,
                           ActivitySimilarity.activity_journal_lo_id == ajournal.id),
                       ActivitySimilarity.constraint == constraint,
                       ActivitySimilarity.similarity > threshold).
                order_by(desc(ActivitySimilarity.similarity)).limit(6).all()]
