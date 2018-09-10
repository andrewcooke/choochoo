
from sqlalchemy import Column, Integer, ForeignKey, Text, UniqueConstraint
from sqlalchemy.ext.orderinglist import ordering_list
from sqlalchemy.orm import relationship, backref

from ..support import Base


class Statistic(Base):

    __tablename__ = 'statistic'

    id = Column(Integer, primary_key=True)
    activity_id = Column(Integer, ForeignKey('activity.id', ondelete='cascade'),
                         nullable=False)
    activity = relationship('Activity',
                            backref=backref('statistics', cascade='all, delete-orphan', passive_deletes=True,
                                            order_by='Statistic.name',
                                            collection_class=ordering_list('name')))
    name = Column(Text, nullable=False)
    units = Column(Text, nullable=False)
    best = Column(Text)  # max, min etc
    UniqueConstraint('activity', 'name')

    def __str__(self):
        return '%s (%s)' % (self.name, self.activity.title)
