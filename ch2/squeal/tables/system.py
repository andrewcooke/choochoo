
from sqlalchemy import Column, Text, Integer

from ..support import Base
from ..types import short_cls, Time, ShortCls, Str


class SystemConstant(Base):

    __tablename__ = 'system_constant'

    name = Column(Text, primary_key=True)
    value = Column(Text, nullable=False)

    TIMEZONE = 'timezone'
    LOCK = 'lock'

    @classmethod
    def is_locked(cls, s):
        s.commit()
        return s.query(SystemConstant). \
            filter(SystemConstant.name == SystemConstant.LOCK).one_or_none()

    @classmethod
    def assert_unlocked(cls, s, allow=None):
        s.commit()
        lock = cls.is_locked(s)
        if lock and (not allow or lock.value != short_cls(allow)):
            raise Exception('Database is locked.  See `ch2 help unlock`.')

    @classmethod
    def acquire_lock(cls, s, owner):
        s.commit()
        cls.assert_unlocked(s, allow=owner)
        s.add(SystemConstant(name=SystemConstant.LOCK, value=short_cls(owner)))
        s.commit()

    @classmethod
    def release_lock(cls, s, owner):
        s.commit()
        s.query(SystemConstant). \
            filter(SystemConstant.name == SystemConstant.LOCK,
                   SystemConstant.value == short_cls(owner)).delete()

    @classmethod
    def reset_lock(cls, s):
        s.commit()
        s.query(SystemConstant). \
            filter(SystemConstant.name == SystemConstant.LOCK).delete()


class SystemWorker(Base):

    __tablename__ = 'system_worker'

    command = Column(Text, nullable=False)
    start = Column(Time, nullable=False)
    owner = Column(ShortCls, nullable=False, index=True)
    constraint = Column(Str, index=True)   # probably not used, but would allow multiple uses by single owner
    pid = Column(Integer, nullable=False, index=True)
