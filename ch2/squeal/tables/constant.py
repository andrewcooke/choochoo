
import datetime as dt
from abc import ABC, abstractmethod
from json import dumps, loads

from sqlalchemy import Column, Integer, ForeignKey, Text, Boolean, desc
from sqlalchemy.orm import relationship
from sqlalchemy.orm.exc import NoResultFound

from .source import Source, SourceType
from .statistic import STATISTIC_JOURNAL_CLASSES, StatisticJournal
from ..types import Cls, Json, lookup_cls
from ...lib.date import local_date_to_time, format_time


class Constant(Source):

    __tablename__ = 'constant'

    id = Column(Integer, ForeignKey('source.id', ondelete='cascade'), primary_key=True)
    # this could be the statistic_name or it could contain more info related to constraint
    name = Column(Text, nullable=False, index=True)
    # todo - this ondelete cascade could cause problems with orphaned sources
    # don't think it's needed anyway, since statistic_name entries are not deleted?
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
        from ch2.squeal.utils import add
        if time and date:
            raise Exception('Specify one or none of time and date for %s' % self)
        if not time and not date:
            time = 0.0  # important this is a float and not an int (or it would be an erroneous date)
        if date:
            time = local_date_to_time(date)
        if time and self.single:
            raise Exception('%s was given time %s but is not time-variable' % (self, format_time(time)))
        sjournal = STATISTIC_JOURNAL_CLASSES[self.statistic_name.statistic_journal_type](
            statistic_name=self.statistic_name, source=self, value=value, time=time)
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
        try:
            return s.query(Constant).filter(Constant.name == name).one()
        except NoResultFound:
            raise Exception('Could not find Constant for %s' % name)

    __mapper_args__ = {
        'polymorphic_identity': SourceType.CONSTANT
    }

    def __str__(self):
        return 'Constant "%s"' % self.name


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


