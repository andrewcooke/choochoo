
import datetime as dt
from re import sub

from urwid import Pile, Text, Columns

from . import Displayer
from ..calculate.segment import SegmentStatistics
from ..names import SEGMENT_TIME, SEGMENT_HEART_RATE
from ...lib.date import local_date_to_time
from ...squeal.tables.activity import ActivityGroup
from ...squeal.tables.segment import SegmentJournal
from ...squeal.tables.statistic import StatisticJournal
from ...uweird.fields import ReadOnlyField
from ...uweird.tui.decorators import Indent


class SegmentDiary(Displayer):

    def _build_date(self, s, f, date):
        tomorrow = local_date_to_time(date + dt.timedelta(days=1))
        today = local_date_to_time(date)
        pile = []
        for activity_group in s.query(ActivityGroup).order_by(ActivityGroup.sort).all():
            segment_pile = []
            for sjournal in s.query(SegmentJournal). \
                    filter(SegmentJournal.start >= today,
                           SegmentJournal.start < tomorrow). \
                    order_by(SegmentJournal.start).all():
                columns = self.__fields(s, date, sjournal, activity_group)
                if columns:
                    segment_pile.append(Columns(columns))
            if segment_pile:
                pile.append(Pile([Text(sjournal.segment.name), Indent(Pile(segment_pile))]))
        if pile:
            yield Pile([Text('Segments'),
                        Indent(Pile(pile))])

    def __fields(self, s, date, sjournal, activity_group):
        time = self.__field(s, date, sjournal, activity_group, SEGMENT_TIME)
        hr = self.__field(s, date, sjournal, activity_group, SEGMENT_HEART_RATE)
        if time or hr:
            return [time if time else Text(''), hr if hr else Text('')]
        else:
            return None

    def __field(self, s, date, sjournal, activity_group, name):
        sjournal = StatisticJournal.at_date(s, date, name, SegmentStatistics, activity_group, source_id=sjournal.id)
        if sjournal:
            return ReadOnlyField(self._log, sjournal, date=date,
                                 format_name=lambda n: sub(r'^Segment ', '', n)).widget()
        else:
            return None

    def _build_schedule(self, s, f, date, schedule=None):
        if False:
            yield None
        return
    #     columns = list(self.__schedule_fields(s, f, date, schedule))
    #     if columns:
    #         yield Pile([Text('Monitor'),
    #                     Indent(Pile(columns))])
    #
    # def __schedule_fields(self, s, f, date, schedule):
    #     names = list(self.__names(s, DAILY_STEPS, REST_HR))
    #     yield from summary_columns(self._log, s, f, date, schedule, names)
    #
    # def __names(self, s, *names):
    #     for name in names:
    #         yield s.query(StatisticName). \
    #             filter(StatisticName.name == name,
    #                    StatisticName.owner == MonitorStatistics).one()
