
from sqlalchemy import Column, Text

from ..support import Base
from ..types import Time, ShortCls


class FileScan(Base):

    __tablename__ = 'file_scan'

    path = Column(Text, nullable=False, primary_key=True)
    owner = Column(ShortCls, nullable=False, primary_key=True)
    md5_hash = Column(Text, nullable=False, index=True)
    last_scan = Column(Time, nullable=False)
