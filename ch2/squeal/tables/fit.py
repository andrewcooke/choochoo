
from sqlalchemy import Column, Text

from ch2.squeal.support import Base
from ch2.squeal.types import Time


class FileScan(Base):

    __tablename__ = 'file_scan'

    path = Column(Text, nullable=False, primary_key=True)
    md5_hash = Column(Text, nullable=False, index=True)
    last_scan = Column(Time, nullable=False)
