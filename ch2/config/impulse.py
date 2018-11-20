
from json import dumps

from .database import add_statistics, add_enum_constant, set_constant
from ..squeal.types import short_cls
from ..stoats.calculate.heart_rate import HeartRateStatistics
from ..stoats.calculate.impulse import HRImpulse, Response, ImpulseStatistics
from ..stoats.calculate.monitor import MonitorStatistics
from ..stoats.names import HR_IMPULSE, FITNESS, FATIGUE


def add_impulse(s, c, activity_group):
    '''
    Add configuration for a fitness/fatigue impulse model based on HR zones.

    This adds:
    * HeartRateStatistics pipeline class to calculate HR zone and impulse
      * Impulse constant with parameters for impulse calculation
    * ImpulseStatistics pipeline class to calculate fitness and fatigue
      * Fitness constant with parameters for fitness calculation
      * Fatigue constant with parameters for fatigue calculation
    '''

    activity_group_constraint = str(activity_group)

    hr_impulse_name = 'HRImpulse.%s' % activity_group.name
    hr_impulse = add_enum_constant(s, hr_impulse_name, HRImpulse, single=True, constraint=activity_group_constraint,
                                   description='Data needed to calculate the FF-model impulse from HR zones - ' +
                                               'see HRImpulse enum')
    set_constant(s, hr_impulse, dumps({'dest_name': HR_IMPULSE, 'gamma': 1.0, 'zero': 2}))

    fitness_name = 'Fitness.%s' % activity_group.name
    fitness = add_enum_constant(s, fitness_name, Response, single=True, constraint=activity_group_constraint,
                                description='Data needed to calculate the FF-model fitness - see Response enum')
    set_constant(s, fitness, dumps({'src_name': HR_IMPULSE, 'src_owner': short_cls(HeartRateStatistics),
                                    'dest_name': FITNESS, 'tau_days': 40, 'scale': 1, 'start': 0}))

    fatigue_name = 'Fatigue.%s' % activity_group.name
    fatigue = add_enum_constant(s, fatigue_name, Response, single=True, constraint=activity_group_constraint,
                                description='Data needed to calculate the FF-model fitness - see Response enum')
    set_constant(s, fatigue, dumps({'src_name': HR_IMPULSE, 'src_owner': short_cls(HeartRateStatistics),
                                    'dest_name': FATIGUE, 'tau_days': 20, 'scale': 1, 'start': 0}))

    add_statistics(s, MonitorStatistics, c, impulse=hr_impulse_name)
    add_statistics(s, ImpulseStatistics, c, responses=(fitness_name, fatigue_name))
