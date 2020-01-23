
from sqlalchemy import Column, Text, Integer, ForeignKey
from sqlalchemy.orm import relationship

from ..support import Base
from ..types import Time, ShortCls
from ..utils import add
from ...lib import to_time


class FileHash(Base):
    '''
    This exists so that hash can be used to connect entities (eg activity topics).
    Entries are never deleted from here (but it's created empty on database updates).
    '''

    __tablename__ = 'file_hash'

    id = Column(Integer, primary_key=True)
    md5 = Column(Text, nullable=False, index=True)

    @classmethod
    def get_or_add(cls, s, md5):
        instance = s.query(FileHash).filter(FileHash.md5 == md5).one_or_none()
        if not instance:
            instance = add(s, FileHash(md5=md5))
        return instance


class FileScan(Base):

    __tablename__ = 'file_scan'

    path = Column(Text, nullable=False, primary_key=True)
    owner = Column(ShortCls, nullable=False, primary_key=True)
    last_scan = Column(Time, nullable=False)
    file_hash_id = Column(Integer, ForeignKey('file_hash.id'), nullable=False)
    file_hash = relationship('FileHash')

    @classmethod
    def add(cls, s, path, owner, md5):
        return add(s, FileScan(path=path, owner=owner, last_scan=to_time(0.0), file_hash=FileHash.get_or_add(s, md5)))

    def __str__(self):
        return self.path
