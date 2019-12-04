
from sqlalchemy import Column, Text, Integer, ForeignKey

from .source import Source, SourceType
from ..types import Time
from ...lib.date import format_time, local_date_to_time


class MonitorJournal(Source):

    __tablename__ = 'monitor_journal'

    id = Column(Integer, ForeignKey('source.id', ondelete='cascade'), primary_key=True)
    fit_file = Column(Text, nullable=False, unique=True)
    start = Column(Time, nullable=False, index=True)
    finish = Column(Time, nullable=False, index=True)

    __mapper_args__ = {
        'polymorphic_identity': SourceType.MONITOR
    }

    def __str__(self):
        return 'Monitor Journal %s to %s' % (format_time(self.start), format_time(self.finish))

    def time_range(self, s):
        return self.start, self.finish

