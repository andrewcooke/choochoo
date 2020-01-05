
from sqlalchemy import Column, UniqueConstraint

from ..support import Base
from ..types import ShortCls, Cls
from ..utils import add
from ...urwid.fields.topic import Integer


class Owner(Base):

    __tablename__ = 'owner'

    id = Column(Integer, primary_key=True)
    # this doesn't really need to be Cls - we only need to go one way
    cls = Column(Cls, nullable=False, index=True)
    UniqueConstraint(cls)

    @classmethod
    def get_or_add(cls, s, owner):
        instance = s.query(Owner).filter(Owner.cls == owner).one_or_none()
        if not instance:
            instance = add(s, Owner(cls=owner))
        return instance


def owner(s, cls):
    if cls:
        return Owner.get_or_add(s, cls)
    else:
        return None
