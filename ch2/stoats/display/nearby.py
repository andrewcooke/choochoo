
from sqlalchemy import or_, desc, distinct
from sqlalchemy.orm import aliased
from sqlalchemy.sql.functions import min
from urwid import Pile, Text, Columns, connect_signal

from . import JournalDiary
from ...lib.date import to_time, time_to_local_date
from ...lib.utils import label
from ...squeal import ActivityJournal, ActivitySimilarity, ActivityNearby
from ...uweird.tui.decorators import Indent
from ...uweird.tui.widgets import ArrowMenu


def _fmt_time(time):
    return to_time(time).strftime('%Y-%m-%d')


def fmt_nearby(aj, nb):
    return to_time(aj.start).strftime('%y-%m-%d') + ' %d%%' % (nb.similarity * 100)


class NearbyDiary(JournalDiary):

    def _display_schedule(self, s, f, date, schedule=None):
        yield from []

    def _journal_date(self, s, f, ajournal, date):
        for constraint in constraints(s):
            row = []
            row += self._any_time(s, f, ajournal, constraint)
            row += self._earlier(s, f, ajournal, constraint)
            row += self._group(s, f, ajournal, constraint)
            if row:
                yield Pile([Text(constraint),
                            Indent(Columns(row))])

    def __change_date(self, w):
        self._diary._change_date(time_to_local_date(w.state))

    def __button(self, f, caption, options):
        if options:
            menu = ArrowMenu(label(caption), options)
            connect_signal(menu, 'click', self.__change_date)
            yield f(menu)

    def _any_time(self, s, f, ajournal, constraint):
        yield from self.__button(f, 'Any Time: ',
                                 dict((aj.start, fmt_nearby(aj, nb)) for aj, nb in
                                      nearby_any_time(s, ajournal, constraint=constraint)))

    def _earlier(self, s, f, ajournal, constraint):
        yield from self.__button(f, 'Earlier: ',
                                 dict((aj.start, fmt_nearby(aj, nb)) for aj, nb in
                                      nearby_earlier(s, ajournal, constraint=constraint)))

    def _group(self, s, f, ajournal, constraint):
        yield from self.__button(f, 'Group: ',
                                 dict((aj.start, _fmt_time(aj.start)) for aj in group(s, ajournal, constraint)))


def constraints(s):
    yield from (c[0] for c in
                s.query(distinct(ActivitySimilarity.constraint)).
                    order_by(ActivitySimilarity.constraint).all())


def group(s, ajournal, constraint):
    nb_us = aliased(ActivityNearby)
    nb_them = aliased(ActivityNearby)
    return [nb.activity_journal
            for nb in s.query(nb_them).
                join(nb_us, nb_us.group == nb_them.group).
                join(ActivityJournal, ActivityJournal.id == nb_them.activity_journal_id).
                filter(nb_us.constraint == constraint,
                       nb_us.activity_journal == ajournal,
                       nb_them.activity_journal != ajournal).
                order_by(ActivityJournal.start)]


def nearby_earlier(s, ajournal, constraint=None, threshold=0.3):
    ajlo = aliased(ActivityJournal)
    ajhi = aliased(ActivityJournal)
    q = s.query(ActivitySimilarity). \
                join(ajhi, ActivitySimilarity.activity_journal_hi_id == ajhi.id). \
                join(ajlo, ActivitySimilarity.activity_journal_lo_id == ajlo.id). \
                filter(or_(ActivitySimilarity.activity_journal_hi_id == ajournal.id,
                           ActivitySimilarity.activity_journal_lo_id == ajournal.id),
                       or_(ajhi.id == ajournal.id, ajhi.start < ajournal.start),
                       or_(ajhi.id == ajournal.id, ajlo.start < ajournal.start),
                       ActivitySimilarity.similarity > threshold). \
                order_by(desc(min(ajlo.start, ajhi.start)))
    if constraint:
        q = q.filter(ActivitySimilarity.constraint == constraint)
    return [(asm.activity_journal_lo if asm.activity_journal_lo != ajournal else asm.activity_journal_hi, asm)
            for asm in q.all()]


def nearby_any_time(s, ajournal, constraint=None, threshold=0.3):
    q = s.query(ActivitySimilarity). \
                filter(or_(ActivitySimilarity.activity_journal_hi_id == ajournal.id,
                           ActivitySimilarity.activity_journal_lo_id == ajournal.id),
                       ActivitySimilarity.similarity > threshold). \
                order_by(desc(ActivitySimilarity.similarity))
    if constraint:
        q = q.filter(ActivitySimilarity.constraint == constraint)
    return [(asm.activity_journal_lo if asm.activity_journal_lo != ajournal else asm.activity_journal_hi, asm)
            for asm in q.all()]
