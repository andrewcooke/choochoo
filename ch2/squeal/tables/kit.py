
from logging import getLogger

from sqlalchemy import Column, Integer, ForeignKey, Text

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
    name = Column(Text, nullable=False, index=True)

    @classmethod
    def get(cls, s, type, force):
        instance = s.query(KitType).filter(KitType.name == type).one_or_none()
        if not instance:
            if force:
                instance = add(s, KitType(name=type))
            else:
                types = s.query(KitType).order_by(KitType.name).all()
                if types:
                    log.info('Existing types:')
                    for type in types:
                        log.info(f'  {type.name}')
                    raise Exception(f'Give an existing type, or specify {mm(FORCE)} to create a new type ({type})')
                else:
                    raise Exception(f'Specify {mm(FORCE)} to create a new type ({type})')
        return instance


class KitItem(Base):

    __tablename__ = 'kit_item'

    id = Column(Integer, primary_key=True)
    type_id = Column(Integer, ForeignKey('kit_type.id', ondelete='cascade'), nullable=False, index=True)
    name = Column(Text, nullable=False, index=True)

    @classmethod
    def new(cls, s, type, name):
        if s.query(KitItem).filter(KitItem.type_id == type.id, KitItem.name == name).one_or_none():
            raise Exception(f'Item {name} of type {type.name} already exists')
        else:
            return add(s, KitItem(type_id=type.id, name=name))


class KitComponent(Base):

    __tablename__ = 'kit_component'

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False, index=True)


class KitPart(Source):

    __tablename__ = 'kit_part'

    id = Column(Integer, ForeignKey('source.id', ondelete='cascade'), primary_key=True)
    item_id = Column(Integer, ForeignKey('kit_item.id', ondelete='cascade'), nullable=False, index=True)
    component_id = Column(Integer, ForeignKey('kit_component.id', ondelete='cascade'), nullable=False, index=True)

    __mapper_args__ = {
        'polymorphic_identity': SourceType.KIT
    }

    def time_range(self, s):
        return None, None

