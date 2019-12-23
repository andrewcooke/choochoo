
from sqlalchemy import or_, desc, distinct
from sqlalchemy.orm import aliased
from sqlalchemy.sql.functions import min
from urwid import Pile, Text, Columns, connect_signal

from . import JournalDiary
from ...diary.model import text, link, menu, optional_label
from ...lib.date import to_time, time_to_local_date, to_date
from ...lib.utils import label
from ...sql import ActivityJournal, ActivitySimilarity, ActivityNearby
from ...urwid.tui.decorators import Indent
from ...urwid.tui.widgets import ArrowMenu


# todo - replace w to_local_date?
def _fmt_time(time):
    return to_time(time).strftime('%Y-%m-%d')


def fmt_nearby(aj, nb):
    return to_time(aj.start).strftime('%y-%m-%d') + ' %d%%' % (nb.similarity * 100)


class NearbyDiary(JournalDiary):

    def _display_schedule(self, s, f, date, schedule):
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

    @optional_label('Nearby', tag='nearbys')
    def _read_journal_date(self, s, ajournal, date):
        for constraint in constraints(s):
            results = list(self.__read_constraint(s, ajournal, constraint))
            if results: yield [text(constraint, tag='nearby')] + results

    def __read_constraint(self, s, ajournal, c):
        for title, callback, fmt in (('Any Time', nearby_any_time,
                                      lambda x: link(fmt_nearby(*x), _fmt_time(x[0].start))),
                                     ('Earlier', nearby_earlier,
                                      lambda x: link(fmt_nearby(*x), _fmt_time(x[0].start))),
                                     ('All', constraint,
                                      lambda x: link(_fmt_time(x.start), _fmt_time(x.start)))):
            links = [fmt(result) for result in callback(s, ajournal, c)]
            if links:
                yield menu(title, links)

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

    def _group(self, s, f, ajournal, constraint_):
        yield from self.__button(f, 'Group: ',
                                 dict((aj.start, _fmt_time(aj.start)) for aj in
                                      constraint(s, ajournal, constraint_)))


def constraints(s):
    yield from (c[0] for c in
                s.query(distinct(ActivitySimilarity.constraint)).
                    order_by(ActivitySimilarity.constraint).all())


def constraint(s, ajournal, constraint):
    nb_us = aliased(ActivityNearby)
    aj_us = aliased(ActivityJournal)
    nb_them = aliased(ActivityNearby)
    aj_them = aliased(ActivityJournal)
    return [nb.activity_journal
            for nb in s.query(nb_them).
                join(nb_us, nb_us.constraint == nb_them.constraint).
                join(aj_them, aj_them.id == nb_them.activity_journal_id).
                join(aj_us, aj_us.id == nb_us.activity_journal_id).
                filter(nb_us.constraint == constraint,
                       nb_us.activity_journal == ajournal,
                       nb_them.activity_journal != ajournal,
                       aj_us.activity_group_id == aj_them.activity_group_id).
                order_by(aj_them.start)]


def nearby_earlier(s, ajournal, constraint=None, threshold=0.3):
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
    if constraint:
        q = q.filter(ActivitySimilarity.constraint == constraint)
    return [(asm.activity_journal_lo if asm.activity_journal_lo != ajournal else asm.activity_journal_hi, asm)
            for asm in q.all()]


def nearby_any_time(s, ajournal, constraint=None, threshold=0.3):
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
    if constraint:
        q = q.filter(ActivitySimilarity.constraint == constraint)
    return [(asm.activity_journal_lo if asm.activity_journal_lo != ajournal else asm.activity_journal_hi, asm)
            for asm in q.all()]
