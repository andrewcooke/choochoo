
import datetime as dt
from logging import getLogger
from re import sub

from urwid import Pile, Text, Columns

from . import Displayer, Reader
from ..calculate.segment import SegmentCalculator
from ..names import SEGMENT_TIME, SEGMENT_HEART_RATE
from ...diary.model import value, text, optional_text
from ...lib.date import local_date_to_time
from ...sql.tables.segment import SegmentJournal, Segment
from ...sql.tables.statistic import StatisticJournal, StatisticName
from ...urwid.fields import ReadOnlyField
from ...urwid.fields.summary import summary_columns
from ...urwid.tui.decorators import Indent

log = getLogger(__name__)


def segments_for_activity(s, ajournal):
    return s.query(SegmentJournal). \
        filter(SegmentJournal.activity_journal == ajournal). \
        order_by(SegmentJournal.start).all()


class SegmentDiary(Displayer, Reader):

    @optional_text('Segments')
    def _read_date(self, s, date):
        tomorrow = local_date_to_time(date + dt.timedelta(days=1))
        today = local_date_to_time(date)
        for sjournal in s.query(SegmentJournal).join(Segment). \
                filter(SegmentJournal.start >= today,
                       SegmentJournal.start < tomorrow). \
                order_by(SegmentJournal.start).all():
            stats = [value(sub('^Segment ', '', field.statistic_name.name), field.value,
                           units=field.statistic_name.units, measures=field.measures_as_model(date))
                     for field in (self.__field(s, date, sjournal, name)
                                   for name in (SEGMENT_TIME, SEGMENT_HEART_RATE))
                     if field]
            if stats:
                yield [text(sjournal.segment.name, tag='segment')] + stats

    def _display_date(self, s, f, date):
        tomorrow = local_date_to_time(date + dt.timedelta(days=1))
        today = local_date_to_time(date)
        pile = []
        for sjournal in s.query(SegmentJournal). \
                join(Segment). \
                filter(SegmentJournal.start >= today,
                       SegmentJournal.start < tomorrow). \
                order_by(SegmentJournal.start).all():
            columns = self.__fields(s, date, sjournal)
            if columns:
                pile.append(Columns(columns))
        if pile:
            yield Pile([Text('Segments'),
                        Indent(Pile(pile))])

    def __fields(self, s, date, sjournal):
        time = self.__field(s, date, sjournal, SEGMENT_TIME)
        hr = self.__field(s, date, sjournal, SEGMENT_HEART_RATE)
        if time or hr:
            return [ReadOnlyField(time, date=date, format_name=lambda n: sub(r'^Segment ', '', n)).widget()
                    if time else Text(''),
                    ReadOnlyField(hr, date=date, format_name=lambda n: sub(r'^Segment ', '', n)).widget()
                    if hr else Text('')]
        else:
            return None

    def __field(self, s, date, sjournal, name):
        return StatisticJournal.at_date(s, date, name, SegmentCalculator, sjournal.segment, source_id=sjournal.id)

    def _display_schedule(self, s, f, date, schedule):
        rows = []
        for segment in s.query(Segment).all():
            segment_rows = list(self.__schedule_fields(s, f, date, segment, schedule))
            if segment_rows:
                segment_rows = Pile([Text(segment.name),
                                     Indent(Pile(segment_rows))])
                rows.append(segment_rows)
        if rows:
            yield Pile([Text('Segments'),
                        Indent(Pile(rows))])

    def __schedule_fields(self, s, f, date, segment, schedule):
        names = list(self.__names(s, segment, SEGMENT_TIME, SEGMENT_HEART_RATE))
        yield from summary_columns(s, f, date, schedule, names,
                                   format_name=lambda n: sub(r'^Segment ', '', n))

    def __names(self, s, segment, *names):
        for name in names:
            sname = s.query(StatisticName). \
                filter(StatisticName.name == name,
                       StatisticName.constraint == segment,
                       StatisticName.owner == SegmentCalculator).one_or_none()
            if sname:
                yield sname
