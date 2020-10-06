
from logging import getLogger

from .database import add_enum_constant, add_process
from ..names import simple_name
from ..pipeline.calculate import ElevationCalculator
from ..pipeline.calculate.power import PowerModel, PowerCalculator, BikeModel

log = getLogger(__name__)

POWER_MODEL_CNAME = 'power-model'


def add_simple_power_estimate(s, activity_group, cda, crr, bike_weight, rider_weight):
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
    add_process(s, PowerCalculator, blocked_by=[ElevationCalculator],
                power_model=power_model.name, activity_group=activity_group.name)


def add_kit_power_estimate(s, activity_groups):
    '''
    Configure parameters indirectly.  This uses a single constant, but must be run for each group.
    The constant doesn't specify the group, so the current group will be used.
    '''
    power_model = add_enum_constant(s, POWER_MODEL_CNAME, PowerModel,
                                    # no activity group is given so the default on expansion will be used
                                    # which will be taken from the context (in this case the activity)
                                    {'bike_model': '${Constant.power-${SegmentReader.kit}}',
                                     'rider_weight': '${DiaryTopic.Weight:}'},
                                    single=True, description='''
Parameters used in estimating power (for the given activity group).

This is the indirect (complex) configuration which delegates to a kit-specific bike model and reads
the weight from a diary entry.
''')
    for activity_group in activity_groups:
        add_process(s, PowerCalculator, blocked_by=[ElevationCalculator],
                    power_model=power_model.name, activity_group=simple_name(activity_group))


def add_kit_power_model(s, kit, activity_group, cda, crr, bike_weight):
    add_enum_constant(s, 'power-' + kit, BikeModel,
                      {'cda': cda, 'crr': crr, 'bike_weight': bike_weight},
                      single=False, activity_group=activity_group, description='''
Parameters used in estimating power (for the given kit and activity group).
* CdA is the coefficient of drag multiplied by frontal area.
* Crr is the coefficient of rolling resistance.
* bike_weight is the weight of the bike.
''')
