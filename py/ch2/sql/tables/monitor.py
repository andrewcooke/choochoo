
from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship, backref

from .source import SourceType, UngroupedSource
from ...common.date import format_time


class MonitorJournal(UngroupedSource):

    __tablename__ = 'monitor_journal'

    id = Column(Integer, ForeignKey('source.id', ondelete='cascade'), primary_key=True)
    file_hash_id = Column(Integer, ForeignKey('file_hash.id'), nullable=False, unique=True)
    file_hash = relationship('FileHash', backref=backref('monitor_journal', uselist=False))
    start = Column(DateTime(timezone=True), nullable=False, index=True)
    finish = Column(DateTime(timezone=True), nullable=False, index=True)

    __mapper_args__ = {
        'polymorphic_identity': SourceType.MONITOR
    }

    def __str__(self):
        return 'Monitor Journal %s to %s' % (format_time(self.start), format_time(self.finish))

    def time_range(self, s):
        return self.start, self.finish

