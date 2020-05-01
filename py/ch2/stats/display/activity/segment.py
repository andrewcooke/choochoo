
import datetime as dt
from logging import getLogger
from re import sub

from ch2.stats.display import Displayer, ActivityJournalDelegate
from ch2.stats.calculate.segment import SegmentCalculator
from ch2.stats.names import SEGMENT_TIME, SEGMENT_HEART_RATE
from ch2.diary.database import summary_column
from ch2.diary.model import value, text, optional_text
from ch2.lib.date import local_date_to_time
from ch2.sql.tables.segment import SegmentJournal, Segment
from ch2.sql.tables.statistic import StatisticJournal, StatisticName

log = getLogger(__name__)


def segments_for_activity(s, ajournal):
    return s.query(SegmentJournal). \
        filter(SegmentJournal.activity_journal == ajournal). \
        order_by(SegmentJournal.start).all()


class SegmentDelegate(ActivityJournalDelegate):

    @optional_text('Segments')
    def read_journal_date(self, s, ajournal, date):
        for sjournal in s.query(SegmentJournal).join(Segment). \
                filter(SegmentJournal.activity_journal_id == ajournal.id). \
                order_by(SegmentJournal.start).all():
            stats = [value(sub('^Segment ', '', field.statistic_name.name), field.value,
                           units=field.statistic_name.units, measures=field.measures_as_model(date))
                     for field in (self.__field(s, date, sjournal, name)
                                   for name in (SEGMENT_TIME, SEGMENT_HEART_RATE))
                     if field]
            if stats:
                yield [text(sjournal.segment.name, tag='segment')] + stats

    @staticmethod
    def __field(s, date, sjournal, name):
        return StatisticJournal.at_date(s, date, name, SegmentCalculator, sjournal.segment, source_id=sjournal.id)

    @optional_text('Segments')
    def read_schedule(self, s, date, schedule):
        for segment in s.query(Segment).all():
            segment_rows = [list(summary_column(s, schedule, date, name))
                            for name in self.__names(s, segment, SEGMENT_TIME, SEGMENT_HEART_RATE)]
            segment_rows = list(filter(bool, segment_rows))
            if segment_rows:
                yield [text(segment.name)] + segment_rows

    @staticmethod
    def __names(s, segment, *names):
        for name in names:
            sname = s.query(StatisticName). \
                filter(StatisticName.name == name,
                       StatisticName.activity_group == segment,
                       StatisticName.owner == SegmentCalculator).one_or_none()
            if sname:
                yield sname


