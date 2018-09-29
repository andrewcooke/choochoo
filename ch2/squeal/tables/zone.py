
from sqlalchemy import Column, Integer, ForeignKey, Float, Text
from sqlalchemy.ext.orderinglist import ordering_list
from sqlalchemy.orm import relationship, backref

from ..support import Base
from ..types import Ordinal


# todo - should these be a statistic?

class HeartRateZones(Base):

    __tablename__ = 'heart_rate_zones'

    id = Column(Integer, primary_key=True)
    date = Column(Ordinal, nullable=False)
    basis = Column(Text)


class HeartRateZone(Base):
    '''
    Following https://www.britishcycling.org.uk/membership/article/20120925-Power-Calculator-0
    we specify zones via the upper limit.

    So HeartRateZones.zones[0].upper_limit is the upper limit HR to zone 1.
    Zone 2 is HeartRateZones.zones[0].upper_limit to  HeartRateZones.zones[1].upper_limit
    etc
    '''

    __tablename__ = 'heart_rate_zone'

    id = Column(Integer, primary_key=True)
    heart_rate_zones_id = Column(Integer, ForeignKey('heart_rate_zones.id'))
    heart_rate_zones = relationship('HeartRateZones',
                                    backref=backref('zones', cascade='all, delete-orphan',
                                                    passive_deletes=True,
                                                    order_by='HeartRateZone.upper_limit',
                                                    collection_class=ordering_list('upper_limit')))
    upper_limit = Column(Integer, nullable=False)
