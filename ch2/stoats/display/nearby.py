
from urwid import Pile, Text

from . import JournalDiary
from ...lib.utils import label
from ...squeal import ActivityNearby
from ...uweird.tui.decorators import Indent


class NearbyDiary(JournalDiary):

    def _build_schedule(self, s, f, date, schedule=None):
        yield from []

    def _journal_date(self, s, ajournal, date):
        for group in s.query(ActivityNearby). \
                filter(ActivityNearby.activity_journal == ajournal):
            nearby = s.query(ActivityNearby). \
                filter(ActivityNearby.constraint == group.constraint,
                       ActivityNearby.group == group.group,
                       ActivityNearby.activity_journal != ajournal).all()
            dates = self._build_dates(nearby)
            yield Pile([Text([label('Nearby: '), group.constraint]),
                        Indent(Text(dates))])

    def _build_dates(self, nearby):
        dates = [d.strftime('%Y-%m-%d')
                 for d in sorted(n.activity_journal.start for n in nearby)]
        if len(dates) < 7:
            return ' '.join(dates)
        else:
            return ' '.join(dates[:3]) + ' ... ' + ' '.join(dates[-3:])
