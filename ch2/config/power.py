
from json import dumps

from . import name_constant, add_enum_constant, set_constant, add_statistics
from ..stoats.calculate.power import Power, ExtendedPowerCalculator

POWER_CNAME = 'Power'


def add_power(s, c, activity_group,
              bike='#$ActivityImporter:Bike', weight='$Topic:Weight:Topic \"Diary\" (d)', p=1.225, g=9.8):
    '''
    Add the constants necessary to estimate power output.
    '''
    activity_group_constraint = str(activity_group)
    power_name = name_constant(POWER_CNAME, activity_group)
    power = add_enum_constant(s, power_name, Power, single=False, constraint=activity_group_constraint,
                              description='Data needed to estimate power - see Power enum')
    set_constant(s, power, dumps({'bike': bike, 'weight': weight, 'p': p, 'g': g}))
    add_statistics(s, ExtendedPowerCalculator, c, power=name_constant(POWER_CNAME, activity_group))
