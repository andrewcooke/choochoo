
from sqlalchemy import Column, Text, Integer, ForeignKey, Index
from sqlalchemy.orm import relationship, backref

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
    hash = Column(Text, nullable=False, index=True, unique=True)

    @classmethod
    def get_or_add(cls, s, hash):
        instance = s.query(FileHash).filter(FileHash.hash == hash).one_or_none()
        if not instance:
            instance = add(s, FileHash(hash=hash))
        return instance


class FileScan(Base):

    __tablename__ = 'file_scan'

    id = Column(Integer, primary_key=True)
    path = Column(Text, nullable=False)
    owner = Column(ShortCls, nullable=False)
    last_scan = Column(Time, nullable=False)
    file_hash_id = Column(Integer, ForeignKey('file_hash.id'), nullable=False)
    file_hash = relationship('FileHash', backref=backref('file_scan', cascade='all, delete-orphan',
                                                         passive_deletes=True, uselist=False))
    Index('natural_primary_file_scan', path, owner)

    @classmethod
    def add(cls, s, path, owner, hash):
        return add(s, FileScan(path=path, owner=owner, last_scan=to_time(0.0), file_hash=FileHash.get_or_add(s, hash)))

    def __str__(self):
        return self.path
