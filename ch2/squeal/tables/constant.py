
import datetime as dt
from abc import ABC, abstractmethod
from json import dumps, loads

from sqlalchemy import Column, Integer, ForeignKey, Text, Boolean, desc
from sqlalchemy.orm import relationship
from sqlalchemy.sql.functions import count

from .source import Source, SourceType
from .statistic import STATISTIC_JOURNAL_CLASSES, StatisticJournal
from ..support import Base
from ..types import Cls, Json, lookup_cls, short_cls
from ...lib.date import local_date_to_time, format_time


class Constant(Source):

    __tablename__ = 'constant'

    id = Column(Integer, ForeignKey('source.id', ondelete='cascade'), primary_key=True)
    statistic_journal_type = Column(Integer, nullable=False)
    # this could be the statistic_name or it could contain more info related to constraint
    name = Column(Text, nullable=False, index=True)
    statistic_name_id = Column(Integer, ForeignKey('statistic_name.id', ondelete='cascade'), nullable=False)
    statistic_name = relationship('StatisticName')
    single = Column(Boolean, nullable=False, server_default='0')
    validate_cls = Column(Cls)
    validate_args = Column(Json, nullable=False, server_default=dumps(()))
    validate_kargs = Column(Json, nullable=False, server_default=dumps({}))

    def validate(self, sjournal):
        if self.validate_cls:
            if self.validate_args is None or self.validate_kargs is None:
                raise Exception('Missing args or kargs for %s' % self)
            validate = self.validate_cls(*self.validate_args, **self.validate_kargs)
            validate.validate(self, sjournal)

    def add_value(self, s, value, time=None, date=None):
        from ..database import add
        if time and date:
            raise Exception('Specify one or none of time and date for %s' % self)
        if not time and not date:
            time = 0.0  # important this is a float and not an int (or it would be an erroneous date)
        if date:
            time = local_date_to_time(date)
        if time and self.single:
            raise Exception('%s was given time %s but is not time-variable' % (self, format_time(time)))
        sjournal = STATISTIC_JOURNAL_CLASSES[self.statistic_journal_type](
            statistic_name=self.statistic_name, source=self, value=value, time=time)
        if self.validate_cls:
            self.validate(sjournal)
        return add(s, sjournal)

    def at(self, s, time=None, date=None):
        if time and date:
            raise Exception('Specify one or none of time and date for %s' % self)
        if date:
            time = local_date_to_time(date)
        if not time:
            time = dt.datetime.now()
        return s.query(StatisticJournal). \
            filter(StatisticJournal.statistic_name == self.statistic_name,
                   StatisticJournal.time <= time). \
            order_by(desc(StatisticJournal.time)).limit(1).one_or_none()

    @classmethod
    def get(cls, s, name):
        return s.query(Constant).filter(Constant.name == name).one()


    __mapper_args__ = {
        'polymorphic_identity': SourceType.CONSTANT
    }

    def __str__(self):
        return 'Constant "%s"' % self.name


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
        lock = s.query(SystemConstant). \
            filter(SystemConstant.name == SystemConstant.LOCK,
                   SystemConstant.value == short_cls(owner)).all()
        if lock:
            for l in lock:
                s.delete(l)
            s.commit()


class Validate(ABC):

    @abstractmethod
    def validate(self, constant, sjournal):
        raise NotImplementedError()


class ValidateError(Exception): pass


class ValidateNamedTuple(Validate):

    def __init__(self, tuple_cls=None):
        if not tuple_cls:
            raise Exception('Add tuple_cls to validator_kargs')
        self.__tuple_cls = lookup_cls(tuple_cls)

    def validate(self, constant, sjournal):
        value = None
        try:
            value = loads(sjournal.value)
        except Exception as e:
            raise ValidateError('Could not unpack JSON value for %s from "%s": %s' %
                                (sjournal.value, constant.name, e))
        try:
            self.__tuple_cls(**value)
        except Exception as e:
            raise ValidateError('Could not create %s from "%s" for "%s": %s' %
                                (self.__tuple_cls, value, constant.name, e))


