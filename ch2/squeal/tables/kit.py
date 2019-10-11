
from logging import getLogger

from sqlalchemy import Column, Integer, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.orm.exc import NoResultFound
from sqlite3 import IntegrityError

from .source import Source, SourceType
from ..support import Base
from ..utils import add
from ...commands.args import FORCE, mm


log = getLogger(__name__)


'''
difficult design decisions here. 
  * too complex for integration with constants.
  * trade-off between simplicity and structure.  no type fo top-level items, for example.
  * all parts are automatically given statistics for description, start, and, when retired, a lifetime.
  * items also get statistics for start and lifetime.
in the end, what drove the design was the commands (see commands/kit.py) - trying to keep them as simple as possible.
'''


class KitType(Base):

    __tablename__ = 'kit_type'

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False, index=True, unique=True)

    @classmethod
    def get(cls, s, type, force):
        try:
            return s.query(KitType).filter(KitType.name == type).one()
        except NoResultFound:
            if force:
                return add(s, KitType(name=type))
            else:
                types = s.query(KitType).order_by(KitType.name).all()
                if types:
                    log.info('Existing types:')
                    for existing in types:
                        log.info(f'  {existing.name}')
                    raise Exception(f'Give an existing type, or specify {mm(FORCE)} to create a new type ({type})')
                else:
                    raise Exception(f'Specify {mm(FORCE)} to create a new type ({type})')


class KitItem(Base):

    __tablename__ = 'kit_item'

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
            return add(s, KitItem(type=type, name=name))

    @classmethod
    def get(cls, s, name):
        try:
            return s.query(KitItem).filter(KitItem.name == name).one()
        except NoResultFound:
            raise Exception(f'Item {name} does not exist')


class KitComponent(Base):

    __tablename__ = 'kit_component'

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False, index=True)

    @classmethod
    def get(cls, s, name, force):
        try:
            return s.query(KitComponent).filter(KitComponent.name == name).one()
        except NoResultFound:
            if force:
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

    id = Column(Integer, ForeignKey('source.id', ondelete='cascade'), primary_key=True)
    item_id = Column(Integer, ForeignKey('kit_item.id', ondelete='cascade'), nullable=False, index=True)
    item = relationship('KitItem')
    component_id = Column(Integer, ForeignKey('kit_component.id', ondelete='cascade'), nullable=False, index=True)
    component = relationship('KitComponent')
    name = Column(Text, nullable=False, index=True)

    @classmethod
    def add(cls, s, item, component, name, date):
        part = cls._add_instance(s, item, component, name)
        cls._add_statistics(s, part, date)
        return part

    @classmethod
    def _add_instance(cls, s, item, component, name):
        if not s.query(KitPart).filter(KitPart.name == name).count():
            log.warning(f'Part name {name} does not match any previous entries')
        return add(s, KitPart(item=item, component=component, name=name))

    @classmethod
    def _add_statistics(cls, s, part, date):
        pass

    __mapper_args__ = {
        'polymorphic_identity': SourceType.KIT
    }

    def time_range(self, s):
        return None, None

