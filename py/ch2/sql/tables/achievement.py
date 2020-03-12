
from logging import getLogger

from sqlalchemy import Column, Text, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import relationship

from ..support import Base


log = getLogger(__name__)


class Achievement(Base):

    __tablename__ = 'achievement'

    id = Column(Integer, primary_key=True)
    text = Column(Text, nullable=False)
    level = Column(Integer, nullable=False)
    activity_journal_id = Column(Integer, ForeignKey('activity_journal.id', ondelete='cascade'),
                                 nullable=False, index=True)
    activity_journal = relationship('ActivityJournal')
    UniqueConstraint(activity_journal_id, text)

