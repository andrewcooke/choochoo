from json import dumps
from logging import getLogger

from . import name_constant, add_enum_constant, set_constant, add_statistics
from ..stats.calculate.power import Power, ExtendedPowerCalculator

log = getLogger(__name__)

POWER_ESTIMATE_CNAME = 'PowerEstimate'


def add_power_estimate(s, c, activity_group,
                       bike='${Constant:Power.${SegmentReader:kit}:None}',
                       rider_weight='${DiaryTopic:Weight:DiaryTopic \"Status\" (d)}',
                       vary='wind_speed, wind_heading, slope'):
    '''
    Add the constants necessary to estimate power output.
    '''
    log.debug(f'Adding power statistics for {activity_group.name}')
    activity_group_constraint = str(activity_group)
    power_name = name_constant(POWER_ESTIMATE_CNAME, activity_group)
    add_enum_constant(s, power_name, Power,
                      {'bike': bike, 'rider_weight': rider_weight, 'vary': vary},
                      single=False, constraint=activity_group_constraint, description='''
Parameters used in estimating power.

These are complex and reference other statistics.  
For example, ${SegmentReader:kit} is the kit specified when the activity is uploaded.

* Bike is an expression that expends to identify a constant named by the kit which itself contains CdA, Crr and weight data for the bike.
* Rider_weight is an expression that expends to read the weight from the diary.
* Vary is an experimental parameter to select what attributes of the ride are modelled (leave blank).
''')
    add_statistics(s, ExtendedPowerCalculator, c, owner_in='[unused - data via activity_statistics]',
                   power=name_constant(POWER_ESTIMATE_CNAME, activity_group),
                   activity_group_name=activity_group.name)
