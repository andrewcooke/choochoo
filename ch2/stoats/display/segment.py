
import datetime as dt
from logging import getLogger
from re import sub

from urwid import Pile, Text, Columns

from . import Displayer
from ..calculate.segment import SegmentCalculator
from ..names import SEGMENT_TIME, SEGMENT_HEART_RATE
from ...lib.date import local_date_to_time
from ...squeal.tables.activity import ActivityGroup
from ...squeal.tables.segment import SegmentJournal, Segment
from ...squeal.tables.statistic import StatisticJournal, StatisticName
from ...uweird.fields import ReadOnlyField
from ...uweird.fields.summary import summary_columns
from ...uweird.tui.decorators import Indent

log = getLogger(__name__)


def segments_for_activity(s, ajournal):
    return s.query(SegmentJournal). \
        filter(SegmentJournal.activity_journal == ajournal). \
        order_by(SegmentJournal.start).all()


class SegmentDiary(Displayer):

    def _display_date(self, s, f, date):
        tomorrow = local_date_to_time(date + dt.timedelta(days=1))
        today = local_date_to_time(date)
        pile = []
        # todo - rewrite to use above
        for agroup in s.query(ActivityGroup).order_by(ActivityGroup.sort).all():
            segment_pile = []
            for sjournal in s.query(SegmentJournal). \
                    join(Segment). \
                    filter(SegmentJournal.start >= today,
                           SegmentJournal.start < tomorrow,
                           Segment.activity_group == agroup). \
                    order_by(SegmentJournal.start).all():
                columns = self.__fields(s, date, sjournal)
                if columns:
                    segment_pile.append(Columns(columns))
            if segment_pile:
                pile.append(Pile([Text(sjournal.segment.name), Indent(Pile(segment_pile))]))
        if pile:
            yield Pile([Text('Segments'),
                        Indent(Pile(pile))])

    def __fields(self, s, date, sjournal):
        time = self.__field(s, date, sjournal, SEGMENT_TIME)
        hr = self.__field(s, date, sjournal, SEGMENT_HEART_RATE)
        if time or hr:
            return [time if time else Text(''), hr if hr else Text('')]
        else:
            return None

    def __field(self, s, date, sjournal, name):
        sjournal = StatisticJournal.at_date(s, date, name, SegmentCalculator, sjournal.segment,
                                            source_id=sjournal.id)
        if sjournal:
            return ReadOnlyField(log, sjournal, date=date,
                                 format_name=lambda n: sub(r'^Segment ', '', n)).widget()
        else:
            return None

    def _display_schedule(self, s, f, date, schedule=None):
        rows = []
        for agroup in s.query(ActivityGroup).order_by(ActivityGroup.sort).all():
            group_rows = []
            for segment in s.query(Segment).filter(Segment.activity_group == agroup).all():
                segment_rows = list(self.__schedule_fields(s, f, date, segment, schedule))
                if segment_rows:
                    segment_rows = Pile([Text(segment.name),
                                         Indent(Pile(segment_rows))])
                    group_rows.append(segment_rows)
            if group_rows:
                group_rows = Pile([Text(agroup.name),
                                   Indent(Pile(group_rows))])
                rows.append(group_rows)
        if rows:
            yield Pile([Text('Segments'),
                        Indent(Pile(rows))])

    def __schedule_fields(self, s, f, date, segment, schedule):
        names = list(self.__names(s, segment, SEGMENT_TIME, SEGMENT_HEART_RATE))
        yield from summary_columns(log, s, f, date, schedule, names,
                                   format_name=lambda n: sub(r'^Segment ', '', n))

    def __names(self, s, segment, *names):
        for name in names:
            sname = s.query(StatisticName). \
                filter(StatisticName.name == name,
                       StatisticName.constraint == segment,
                       StatisticName.owner == SegmentCalculator).one_or_none()
            if sname:
                yield sname
