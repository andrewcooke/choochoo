from collections import defaultdict
from logging import getLogger

from sqlalchemy import Column, Integer, ForeignKey, Text, desc, or_
from sqlalchemy.orm import relationship, aliased
from sqlalchemy.orm.exc import NoResultFound

from ch2.lib.date import local_time_or_now, now
from .source import Source, SourceType, Composite, CompositeComponent
from .statistic import StatisticJournal, StatisticName, StatisticJournalTimestamp
from ..support import Base
from ..utils import add
from ...commands.args import FORCE, mm
from ...stoats.names import KIT_ADDED, KIT_RETIRED, KIT_USED, ACTIVE_TIME, ACTIVE_DISTANCE

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


def get_name(s, name):
    for cls in KitGroup, KitItem, KitComponent, KitModel:
        # can be multiple models, in which case we return one 'at random'
        instance = s.query(cls).filter(cls.name == name).first()
        if instance:
            return instance


def assert_name_does_not_exist(s, name, use):
    instance = get_name(s, name)
    if instance and not isinstance(instance, use):
        raise Exception(f'The name "{name}" is already used for a {type(instance).SIMPLE_NAME}')


def expand_item(s, name, time):
    try:
        item = s.query(KitItem).filter(KitItem.name == name).one()
        start, finish = item.time_added(s), item.time_expired(s)
        if start <= time and (not finish or finish >= time):
            log.debug(f'Found {item}')
            yield item
            for model in s.query(KitModel).filter(KitModel.item == item).all():
                start, finish = model.time_added(s), model.time_expired(s)
                if start <= time and (not finish or finish >= time):
                    log.debug(f'Found {model}')
                    yield model
                else:
                    log.debug(f'Outside time {start} <= {time} <= {finish}')
        else:
            log.debug(f'Outside time {start} <= {time} <= {finish}')
    except NoResultFound as e:
        log.error(e)
        raise Exception(f'Kit item {name} not defined')


class StatisticsMixin:
    '''
    support for reading and writing statistics related to a kit class.
    '''

    def _base_statistic_query(self, s, statistic, *sources, owner=None):
        sources = (self,) + sources
        subq = s.query(Composite.id.label('composite_id'))
        for source in sources:
            cc = aliased(CompositeComponent)
            subq = subq.join(cc, Composite.id == cc.output_source_id).filter(cc.input_source == source)
        subq = subq.subquery()
        q = s.query(StatisticJournal).\
            join(StatisticName).\
            outerjoin(subq, subq.c.composite_id == StatisticJournal.source_id).\
            filter(StatisticName.name == statistic,
                   StatisticName.constraint == None)
        if len(sources) == 1:
            q = q.filter(or_(StatisticJournal.source == self, subq.c.composite_id != None))
        else:
            q = q.filter(subq.c.composite_id != None)
        if owner:
            q = q.filter(StatisticName.owner == owner)
        return q

    def _base_use_query(self, s, statistic):
        cc1, cc2 = aliased(CompositeComponent), aliased(CompositeComponent)
        sourceq = s.query(cc1.input_source_id).\
            join(Composite, Composite.id == cc1.output_source_id).\
            join(cc2, cc2.output_source_id == Composite.id).\
            filter(cc2.input_source == self,
                   cc1.input_source != self).subquery()
        return s.query(StatisticJournal).\
            join(StatisticName).\
            filter(StatisticName.name == statistic,
                   StatisticJournal.source_id.in_(sourceq))

    def _get_statistic(self, s, statistic, *sources, owner=None):
        return self._base_statistic_query(s, statistic, *sources, owner=owner).one_or_none()

    def _get_statistics(self, s, statistic, *sources, owner=None):
        return self._base_statistic_query(s, statistic, *sources, owner=owner).all()

    def _remove_statistic(self, s, statistic, *sources, owner=None):
        # cannot delete directly with join
        for instance in self._get_statistics(s, statistic, *sources, owner=owner):
            s.delete(instance)

    def _add_timestamp(self, s, statistic, time, source=None, owner=None):
        # if source is given it is in addition to self
        if source:
            source = Composite.create(s, source, self)
        else:
            source = self
        owner = owner or self
        return StatisticJournalTimestamp.add(s, statistic, None, None, owner, None, source, time)

    def time_added(self, s):
        return self._get_statistic(s, KIT_ADDED).time

    def time_expired(self, s):
        try:
            return self._get_statistic(s, KIT_RETIRED).time
        except AttributeError:
            return None

    def add_use(self, s, time, source=None, owner=None):
        self._add_timestamp(s, KIT_USED, time, source=source, owner=owner)

    def active_times(self, s):
        return self._base_use_query(s, ACTIVE_TIME).all()

    def active_distances(self, s):
        return self._base_use_query(s, ACTIVE_DISTANCE).all()

    def lifetime(self, s):
        added, expired = self.time_added(s), self.time_expired(s)
        expired = expired or now()
        return expired - added


class KitGroup(Base):
    '''
    top level group for kit (bike, shoe, etc)
    '''

    __tablename__ = 'kit_group'
    SIMPLE_NAME = 'group'

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False, index=True, unique=True)

    @classmethod
    def get(cls, s, name, force=False):
        try:
            return s.query(KitGroup).filter(KitGroup.name == name).one()
        except NoResultFound:
            assert_name_does_not_exist(s, name, KitGroup)
            if force:
                log.warning(f'Forcing creation of new group ({name})')
                return add(s, KitGroup(name=name))
            else:
                groups =\
                    s.query(KitGroup).order_by(KitGroup.name).all()
                if groups:
                    log.info('Existing groups:')
                    for existing in groups:
                        log.info(f'  {existing.name}')
                    raise Exception(f'Give an existing group, or specify {mm(FORCE)} to create a new group ({name})')
                else:
                    raise Exception(f'Specify {mm(FORCE)} to create a new group ({name})')

    def __str__(self):
        return f'KitGroup "{self.name}"'


class KitItem(StatisticsMixin, Source):
    '''
    an individual kit item (a particular bike, a particular shoe, etc)
    '''

    __tablename__ = 'kit_item'
    SIMPLE_NAME = 'item'

    id = Column(Integer, ForeignKey('source.id', ondelete='cascade'), primary_key=True)
    group_id = Column(Integer, ForeignKey('kit_group.id', ondelete='cascade'), nullable=False, index=True)
    group = relationship('KitGroup', backref='items')
    name = Column(Text, nullable=False, index=True, unique=True)

    __mapper_args__ = {
        'polymorphic_identity': SourceType.ITEM
    }

    @classmethod
    def new(cls, s, group, name, date):
        time = local_time_or_now(date)
        # don't rely on unique index to catch duplicates because that's not triggered until commit
        if s.query(KitItem).filter(KitItem.name == name).count():
            raise Exception(f'Item {name} of group {group.name} already exists')
        else:
            assert_name_does_not_exist(s, name, KitItem)
            item = add(s, KitItem(group=group, name=name))
            item._add_statistics(s, time)
            return item

    def _add_statistics(self, s, time):
        self._add_timestamp(s, KIT_ADDED, time)

    @classmethod
    def get(cls, s, name):
        try:
            return s.query(KitItem).filter(KitItem.name == name).one()
        except NoResultFound:
            raise Exception(f'Item {name} does not exist')

    @property
    def components(self):
        components = defaultdict(list)
        for model in self.models:
            components[model.component].append(model)
        return components

    def __str__(self):
        return f'KitItem "{self.name}"'


class KitComponent(Base):
    '''
    the kind of thing that a kit item is made of (bike wheel, shoe laces, etc)
    '''

    __tablename__ = 'kit_component'
    SIMPLE_NAME = 'component'

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False, index=True)

    @classmethod
    def get(cls, s, name, force):
        try:
            return s.query(KitComponent).filter(KitComponent.name == name).one()
        except NoResultFound:
            assert_name_does_not_exist(s, name, KitComponent)
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

    def __str__(self):
        return f'KitComponent "{self.name}"'


class KitModel(StatisticsMixin, Source):
    '''
    a particular piece of a a kit item (a particular bike wheel, a particulae set of laces, etc).
    '''

    __tablename__ = 'kit_model'
    SIMPLE_NAME = 'model'

    id = Column(Integer, ForeignKey('source.id', ondelete='cascade'), primary_key=True)
    item_id = Column(Integer, ForeignKey('kit_item.id', ondelete='cascade'), nullable=False, index=True)
    item = relationship('KitItem', foreign_keys=[item_id], backref='models')
    component_id = Column(Integer, ForeignKey('kit_component.id', ondelete='cascade'), nullable=False, index=True)
    component = relationship('KitComponent')
    name = Column(Text, nullable=False, index=True)

    __mapper_args__ = {
        'polymorphic_identity': SourceType.MODEL
    }

    @classmethod
    def add(cls, s, item, component, name, date, force):
        time = local_time_or_now(date)
        cls._reject_duplicate(s, item, component, name, time)
        model = cls._add_instance(s, item, component, name)
        model._add_statistics(s, time, force)
        return model

    @classmethod
    def _reject_duplicate(cls, s, item, component, name, time):
        if s.query(StatisticJournal).\
                join(StatisticName).\
                join(KitModel, KitModel.id == StatisticJournal.source_id).\
                filter(StatisticName.name == KIT_ADDED,
                       StatisticJournal.time == time,
                       KitModel.name == name,
                       KitModel.component == component,
                       KitModel.item == item).count():
            raise Exception(f'This part already exists at this date')

    @classmethod
    def _add_instance(cls, s, item, component, name):
        # TODO - restrict name to a particular component
        if not s.query(KitModel).filter(KitModel.name == name).count():
            assert_name_does_not_exist(s, name, KitModel)
            log.warning(f'Model {name} does not match any previous entries')
        return add(s, KitModel(item=item, component=component, name=name))

    def time_range(self, s):
        return None, None

    def _add_statistics(self, s, time, force):
        self._add_timestamp(s, KIT_ADDED, time)
        before = self.before(s, time)
        after = self.after(s, time)
        if before:
            before_expiry = before.time_expired(s)
            if before_expiry and before_expiry > time:
                before._remove_statistic(s, KIT_RETIRED)
                before_expiry = None
            if not before_expiry:
                before._add_timestamp(s, KIT_RETIRED, time)
                log.info(f'Expired previous {self.component.name} ({before.name})')
        if after:
            after_added = after.time_added(s)
            self._add_timestamp(s, KIT_RETIRED, after_added)
            log.info(f'Expired new {self.component.name} ({self.name})')

    def _base_sibling_query(self, s, statistic):
        return s.query(KitModel).\
                join(StatisticJournal, StatisticJournal.source_id == KitModel.id).\
                join(StatisticName).\
                join(KitComponent, KitComponent.id == KitModel.component_id).\
                join(KitItem, KitItem.id == KitModel.item_id).\
                filter(StatisticName.name == statistic,
                       KitComponent.name == self.component.name,
                       KitItem.name == self.item.name)

    def before(self, s, time=None):
        if not time:
            time = self.time_added(s)
        return self._base_sibling_query(s, KIT_ADDED).filter(StatisticJournal.time < time).\
            order_by(desc(StatisticJournal.time)).first()

    def after(self, s, time=None):
        if not time:
            time = self.time_added(s)
        return self._base_sibling_query(s, KIT_ADDED).filter(StatisticJournal.time > time).\
            order_by(StatisticJournal.time).first()

    def __str__(self):
        return f'KitModel "{self.name}"'
