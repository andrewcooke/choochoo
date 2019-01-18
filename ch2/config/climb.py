
from json import dumps

from ch2.config import name_constant, add_enum_constant, set_constant
from ch2.stoats.calculate.climb import Climb

CLIMB_CNAME = 'Climb'


def add_climb(s, activity_group, phi=0.6):
    '''
    Add the constants necessary to auto-detect climbs.
    '''
    activity_group_constraint = str(activity_group)
    fatigue_name = name_constant(CLIMB_CNAME, activity_group)
    fatigue = add_enum_constant(s, fatigue_name, Climb, single=True, constraint=activity_group_constraint,
                                description='Data needed to cdetect climbs - see Climb enum')
    set_constant(s, fatigue, dumps({'phi': phi, 'min_gradient': 3, 'min_elevation': 80, 'max_reversal': 0.1}))
