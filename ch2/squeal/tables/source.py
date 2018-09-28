
from ch2.squeal.support import Base


class Source(Base):

    __tablename__ = 'source'

    id = Column(Integer, primary_key=True)
    type = Column(Integer, nullable=False)
    time = Column(Epoch, nullable=False)

    __mapper_args__ = {
        'polymorphic_identity': 0,
        'polymorphic_on': type
    }


