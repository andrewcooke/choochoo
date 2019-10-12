
import datetime as dt
from logging import getLogger

from sqlalchemy import Column, Integer, ForeignKey, Text, desc
from sqlalchemy.orm import relationship
from sqlalchemy.orm.exc import NoResultFound

from .source import Source, SourceType
from .statistic import StatisticJournal, StatisticName, StatisticJournalText, StatisticJournalFloat
from ..support import Base
from ..utils import add
from ...commands.args import FORCE, mm
from ...lib import local_time_to_time, format_seconds
from ...stoats.names import PART_ADDED, PART_EXPIRED, PART_LIFETIME, S, summaries, MAX, MIN, CNT, AVG

log = getLogger(__name__)


'''
difficult design decisions here. 
  * too complex for integration with constants.
  * trade-off between simplicity and structure.  no type fo top-level items, for example.
  * all parts are automatically given statistics for description, start, and, when retired, a lifetime.
  * items also get statistics for start and lifetime.
in the end, what drove the design was the commands (see commands/kit.py) - trying to keep them as simple as possible.
unfortunately that pushed some extra complexity into the data model (eg to guarantee all names unique).
'''


def find_name(s, name):
    for cls in KitType, KitItem, KitComponent, KitPart:
        instance = s.query(cls).filter(cls.name == name).one_or_none()
        if instance:
            return instance


def check_name(s, name, use):
    instance = find_name(s, name)
    if instance and not isinstance(instance, use):
        raise Exception(f'The name "{name}" is already used for a {type(instance).SIMPLE_NAME}')


class KitType(Base):

    __tablename__ = 'kit_type'
    SIMPLE_NAME = 'type'

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False, index=True, unique=True)

    @classmethod
    def get(cls, s, name, force):
        try:
            return s.query(KitType).filter(KitType.name == name).one()
        except NoResultFound:
            check_name(s, name, KitType)
            if force:
                log.warning(f'Forcing creation of new type ({name})')
                return add(s, KitType(name=name))
            else:
                types =\
                    s.query(KitType).order_by(KitType.name).all()
                if types:
                    log.info('Existing types:')
                    for existing in types:
                        log.info(f'  {existing.name}')
                    raise Exception(f'Give an existing type, or specify {mm(FORCE)} to create a new type ({name})')
                else:
                    raise Exception(f'Specify {mm(FORCE)} to create a new type ({name})')


class KitItem(Base):

    __tablename__ = 'kit_item'
    SIMPLE_NAME = 'item'

    id = Column(Integer, primary_key=True)
    type_id = Column(Integer, ForeignKey('kit_type.id', ondelete='cascade'), nullable=False, index=True)
    type = relationship('KitType')
    name = Column(Text, nullable=False, index=True, unique=True)

    @classmethod
    def new(cls, s, type, name):
        # don't rely on unique index to catch duplicates because that's not triggered until commit
        if s.query(KitItem).filter(KitItem.name == name).count():
            raise Exception(f'Item {name} of type {type.name} already exists')
        else:
            check_name(s, name, KitItem)
            return add(s, KitItem(type=type, name=name))

    @classmethod
    def get(cls, s, name):
        try:
            return s.query(KitItem).filter(KitItem.name == name).one()
        except NoResultFound:
            raise Exception(f'Item {name} does not exist')


class KitComponent(Base):

    __tablename__ = 'kit_component'
    SIMPLE_NAME = 'component'

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False, index=True)

    @classmethod
    def get(cls, s, name, force):
        try:
            return s.query(KitComponent).filter(KitComponent.name == name).one()
        except NoResultFound:
            check_name(s, name, KitComponent)
            if force:
                log.warning(f'Forcing creation of new component ({name})')
                return add(s, KitComponent(name=name))
            else:
                components = s.query(KitComponent).order_by(KitComponent.name).all()
                if components:
                    log.info('Existing components:')
                    for existing in components:
                        log.info(f'  {existing.name}')
                    raise Exception(f'Give an existing component, or specify {mm(FORCE)} to create a new one ({name})')
                else:
                    raise Exception(f'Specify {mm(FORCE)} to create a new component ({name})')


class KitPart(Source):

    __tablename__ = 'kit_part'
    SIMPLE_NAME = 'part'

    id = Column(Integer, ForeignKey('source.id', ondelete='cascade'), primary_key=True)
    item_id = Column(Integer, ForeignKey('kit_item.id', ondelete='cascade'), nullable=False, index=True)
    item = relationship('KitItem')
    component_id = Column(Integer, ForeignKey('kit_component.id', ondelete='cascade'), nullable=False, index=True)
    component = relationship('KitComponent')
    name = Column(Text, nullable=False, index=True)

    @classmethod
    def add(cls, s, item, component, name, date, force):
        if date:
            time = local_time_to_time(date)
        else:
            time = dt.datetime.now(tz=dt.timezone.utc)
        part = cls._add_instance(s, item, component, name)
        part._add_statistics(s, time, force)
        return part

    @classmethod
    def _reject_duplicate(cls, s, item, component, name, time):
        if s.query(StatisticJournal).\
                join(StatisticName).join(KitPart).join(Source).join(KitComponent).join(KitItem).\
                filter(StatisticName.name == PART_ADDED,
                       StatisticJournal.time == time,
                       KitPart.name == name,
                       KitComponent.name == component,
                       KitItem.name == item).count():
            raise Exception(f'This part already exists at this date')

    @classmethod
    def _add_instance(cls, s, item, component, name):
        if not s.query(KitPart).filter(KitPart.name == name).count():
            check_name(s, name, KitPart)
            log.warning(f'Part name {name} does not match any previous entries')
        return add(s, KitPart(item=item, component=component, name=name))

    __mapper_args__ = {
        'polymorphic_identity': SourceType.KIT
    }

    def time_range(self, s):
        return None, None

    def _add_statistics(self, s, time, force):
        self._add_timestamp(s, PART_ADDED, time)
        before = self.before(s, time)
        after = self.after(s, time)
        if before:
            before_expiry = before.time_expired(s)
            if before_expiry and before_expiry > time:
                before._remove_statistic(s, PART_EXPIRED)
                before._remove_statistic(s, PART_LIFETIME)
                before_expiry = None
            if not before_expiry:
                before._add_timestamp(s, PART_EXPIRED, time)
                lifetime = (time - before.time_added(s)).total_seconds()
                before._add_lifetime(s, lifetime, time)
                log.info(f'Expired previous {self.component.name} ({before.name}) - '
                         f'lifetime of {format_seconds(lifetime)}')
        if after:
            after_added = after.time_added(s)
            self._add_timestamp(s, PART_EXPIRED, after_added)
            lifetime = (after_added - time).total_seconds()
            self._add_lifetime(s, lifetime, after_added)
            log.info(f'Expired new {self.component.name} ({self.name}) - '
                     f'lifetime of {format_seconds(lifetime)}')

    def _get_statistic(self, s, statistic):
        return s.query(StatisticJournal).\
                join(StatisticName).\
                filter(StatisticName.name == statistic,
                       StatisticJournal.source == self).one_or_none()

    def _remove_statistic(self, s, statistic):
        s.query(StatisticJournal).\
                join(StatisticName).\
                filter(StatisticName.name == statistic,
                       StatisticJournal.source == self).delete()

    def _add_timestamp(self, s, statistic, time):
        return StatisticJournalText.add(s, statistic, None, None, self, None, self, str(self), time)

    def _add_lifetime(self, s, lifetime, time):
        return StatisticJournalFloat.add(s, PART_LIFETIME, S, summaries(MAX, MIN, CNT, AVG), self, None, self,
                                         lifetime, time)

    def time_added(self, s):
        return self._get_statistic(s, PART_ADDED).time

    def time_expired(self, s):
        try:
            return self._get_statistic(s, PART_EXPIRED).time
        except AttributeError:
            return None

    def _base_sibling_query(self, s, statistic):
        return s.query(KitPart).\
                join(StatisticJournal).join(StatisticName).join(KitComponent).join(KitItem).\
                filter(StatisticName.name == statistic,
                       KitComponent.name == self.component.name,
                       KitItem.name == self.item.name)

    def before(self, s, time=None):
        if not time:
            time = self.time_added(s)
        return self._base_sibling_query(s, PART_ADDED).filter(StatisticJournal.time < time).\
            order_by(desc(StatisticJournal.time)).first()

    def after(self, s, time=None):
        if not time:
            time = self.time_added(s)
        return self._base_sibling_query(s, PART_ADDED).filter(StatisticJournal.time > time).\
            order_by(StatisticJournal.time).first()

    def __str__(self):
        return f'{self.item.type.name} {self.item.name} {self.component.name} {self.name}'


