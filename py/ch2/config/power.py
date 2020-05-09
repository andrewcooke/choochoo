
from logging import getLogger

from .database import add_enum_constant, add_statistics
from ..pipeline.calculate.power import Power, ExtendedPowerCalculator

log = getLogger(__name__)

POWER_ESTIMATE_CNAME = 'power_estimate'


def add_power_estimate(s, c, activity_group, bike=None,
                       rider_weight='${DiaryTopic:Weight:All}',
                       vary='wind_speed, wind_heading, slope'):
    '''
    Add the constants necessary to estimate power output.
    '''
    log.debug(f'Adding power statistics for {activity_group.name}')
    if not bike: bike = '${Constant:Power.${SegmentReader:kit:%s}:All}' % activity_group.name
    constant = add_enum_constant(s, POWER_ESTIMATE_CNAME, Power,
                                 {'bike': bike, 'rider_weight': rider_weight, 'vary': vary},
                                 single=False, activity_group=activity_group.name, description='''
Parameters used in estimating power.

These are complex and reference other statistics.  
For example, ${SegmentReader:kit} is the kit specified when the activity is uploaded.
* Bike is an expression that expends to identify a constant named by the kit which itself contains CdA, Crr and weight data for the bike.
* Rider_weight is an expression that expends to read the weight from the diary.
* Vary is an experimental parameter to select what attributes of the ride are modelled (leave blank).
''')
    add_statistics(s, ExtendedPowerCalculator, c, power=constant.name, activity_group=activity_group.name)
