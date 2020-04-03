
from json import dumps
from logging import getLogger

from . import name_constant, add_enum_constant, set_constant
from ..data.climb import Climb, MAX_CLIMB_GRADIENT, MIN_CLIMB_GRADIENT, MAX_CLIMB_REVERSAL, \
    MIN_CLIMB_ELEVATION

log = getLogger(__name__)

CLIMB_CNAME = 'Climb'


def add_climb(s, phi=0.7):
    '''
    Add the constants necessary to auto-detect climbs.
    '''
    log.debug('Adding climb parameters')
    climb = add_enum_constant(s, CLIMB_CNAME, Climb, single=True,
                              description='Data needed to detect climbs - see Climb enum')
    set_constant(s, climb, dumps({'phi': phi,
                                  'min_gradient': MIN_CLIMB_GRADIENT,
                                  'max_gradient': MAX_CLIMB_GRADIENT,
                                  'min_elevation': MIN_CLIMB_ELEVATION,
                                  'max_reversal': MAX_CLIMB_REVERSAL}))
