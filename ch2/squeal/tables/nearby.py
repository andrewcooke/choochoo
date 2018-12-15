
from sqlalchemy import Column, Integer, ForeignKey, Float, Text

from ..support import Base


class NearbySimilarity(Base):

    __tablename__ = 'nearby_similarity'

    id = Column(Integer, primary_key=True)
    label = Column(Text, index=True)
    activity_journal_lo_id = Column(Integer, ForeignKey('activity_journal.id', ondelete='cascade'), index=True)
    activity_journal_hi_id = Column(Integer, ForeignKey('activity_journal.id', ondelete='cascade'), index=True)
    similarity = Column(Float, nullable=False)
