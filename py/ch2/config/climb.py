from logging import getLogger

from .database import add_enum_constant
from ..data.climb import Climb, MAX_CLIMB_GRADIENT, MIN_CLIMB_GRADIENT, MAX_CLIMB_REVERSAL, \
    MIN_CLIMB_ELEVATION

log = getLogger(__name__)

CLIMB_CNAME = 'Climb'


def add_climb(s, phi=0.7):
    '''
    Add the constants necessary to auto-detect climbs.
    '''
    log.debug('Adding climb parameters')
    add_enum_constant(s, CLIMB_CNAME, Climb,
                      {'phi': phi,
                       'min_gradient': MIN_CLIMB_GRADIENT,
                       'max_gradient': MAX_CLIMB_GRADIENT,
                       'min_elevation': MIN_CLIMB_ELEVATION,
                       'max_reversal': MAX_CLIMB_REVERSAL},
                      single=True, description='''
Parameters used by climb detection.
* Phi is an exponent used to weight the relative steepness of candidates and should be around 1 (typical range 0.5 to 2).
* Min_gradient is the minimum gradient for a climb (units %).
* Min_elevation is the minimum elevation for a climb (units m) (this, together with min_gradient, implies a minimum distance).
* Max_reversal is the fractional descent allowed within a climb (if it has a value of 0.5 then you can descend half the climbed distance).
                              ''')
