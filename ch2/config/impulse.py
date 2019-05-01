
from json import dumps

from .database import add_statistics, add_enum_constant, set_constant, name_constant
from ..squeal.types import short_cls
from ..stoats.calculate.heart_rate import HRImpulse, HeartRateCalculator
from ..stoats.calculate.impulse import Response, ImpulseCalculator
from ..stoats.names import HR_IMPULSE, FITNESS_D, FATIGUE_D
from ..stoats.read.segment import SegmentReader


def add_impulse(s, c, activity_group, start=1e-6, fitness=((42, 1),), fatigue=((7, 5),)):
    '''
    Add configuration for a fitness/fatigue impulse model based on HR zones.

    This adds:
    * HeartRateCalculator pipeline class to calculate HR zone and impulse
      * Impulse constant with parameters for impulse calculation
    * ImpulseCalculator pipeline class to calculate fitness and fatigue
      * Fitness constant with parameters for fitness calculation
      * Fatigue constant with parameters for fatigue calculation
    '''

    activity_group_constraint = str(activity_group)
    responses = []

    hr_impulse_name = name_constant('HRImpulse', activity_group)
    hr_impulse = add_enum_constant(s, hr_impulse_name, HRImpulse, single=True,
                                   constraint=activity_group_constraint,
                                   description='Data needed to calculate the FF-model impulse from HR zones - ' +
                                               'see HRImpulse enum')
    set_constant(s, hr_impulse, dumps({'dest_name': HR_IMPULSE, 'gamma': 2.0, 'zero': 2, 'max_secs': 60}))

    for days, scale in fitness:
        name = FITNESS_D % days
        constant = name_constant(name, activity_group)
        responses.append(constant)
        fitness = add_enum_constant(s, constant, Response, single=True, constraint=activity_group_constraint,
                                    description=f'Data needed to calculate the FF-model fitness for {days}d - ' +
                                    'see Response enum')
        set_constant(s, fitness, dumps({'src_name': HR_IMPULSE, 'src_owner': short_cls(HeartRateCalculator),
                                        'dest_name': name, 'tau_days': days, 'scale': scale, 'start': start}))

    for days, scale in fatigue:
        name = FATIGUE_D % days
        constant = name_constant(name, activity_group)
        responses.append(constant)
        fitness = add_enum_constant(s, constant, Response, single=True, constraint=activity_group_constraint,
                                    description=f'Data needed to calculate the FF-model fatigue for {days}d - ' +
                                    'see Response enum')
        set_constant(s, fitness, dumps({'src_name': HR_IMPULSE, 'src_owner': short_cls(HeartRateCalculator),
                                        'dest_name': name, 'tau_days': days, 'scale': scale, 'start': start}))

    add_statistics(s, HeartRateCalculator, c, owner_in=short_cls(SegmentReader),
                   impulse=hr_impulse_name)
    add_statistics(s, ImpulseCalculator, c, owner_in=short_cls(HeartRateCalculator),
                   responses=responses, impulse=hr_impulse_name)
