
from logging import getLogger

from .database import add_enum_constant, add_statistics
from ..pipeline.calculate.power import PowerModel, PowerCalculator

log = getLogger(__name__)

POWER_MODEL_CNAME = 'power-model'


def add_simple_power_estimate(s, c, activity_group, cda, crr, bike_weight, rider_weight):
    '''
    Configure parameters directly.
    '''
    power_model = add_enum_constant(s, POWER_MODEL_CNAME, PowerModel,
                                    {'bike_model': {'cda': cda, 'crr': crr, 'bike_weight': bike_weight},
                                     'rider_weight': rider_weight},
                                    single=False, activity_group=activity_group, description='''
Parameters used in estimating power (for the given activity group).

This is the direct (simpler) configuration (unless it has been modified).  
The physical parameters are encoded directly below.
* CdA is the coefficient of drag multiplied by frontal area.
* Crr is the coefficient of rolling resistance.
* bike_weight is the weight of the bike.
* rider_weight is the weight of the rider.
In more complex configurations these can be references to other constants.
''')
    add_statistics(s, PowerCalculator, c, power_model=power_model.name, activity_group=activity_group.name)


def add_kit_power_estimate(s, c, activity_group):
    '''
    Configure parameters indirectly.
    '''
    pass
