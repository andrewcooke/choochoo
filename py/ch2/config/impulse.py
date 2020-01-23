
from json import dumps

from .database import add_statistics, add_enum_constant, set_constant, name_constant
from ..sql import ActivityGroup
from ..sql.types import short_cls
from ..stats.calculate.impulse import HRImpulse, ImpulseCalculator
from ..stats.calculate.response import Response, ResponseCalculator
from ..stats.names import FITNESS_D, FATIGUE_D, ALL
from ..stats.read.segment import SegmentReader


def add_impulse(s, c, activity_group):
    '''
    Add configuration for a fitness/fatigue impulse model based on HR zones.

    This adds:
    * HeartRateCalculator pipeline class to calculate HR zone and impulse
      * Impulse constant with parameters for impulse calculation
    * ImpulseCalculator pipeline class to calculate fitness and fatigue
      * Fitness constant with parameters for fitness calculation
      * Fatigue constant with parameters for fatigue calculation
    '''

    hr_impulse_name = name_constant('HRImpulse', activity_group)
    hr_impulse = add_enum_constant(s, hr_impulse_name, HRImpulse, single=True, constraint=activity_group,
                                   description='Data needed to calculate the FF-model impulse from HR zones - ' +
                                               'see HRImpulse enum')
    set_constant(s, hr_impulse, dumps({'gamma': 2.0, 'zero': 1, 'one': 6, 'max_secs': 60}))

    add_statistics(s, ImpulseCalculator, c, owner_in=short_cls(SegmentReader), impulse_ref=hr_impulse_name)


def add_responses(s, c, fitness=((42, 1, 1),), fatigue=((7, 1, 5),)):

    responses = []
    all = ActivityGroup.from_name(s, ALL)

    for days, start, scale in fitness:
        name = FITNESS_D % days
        constant = name_constant(name, all)
        responses.append(constant)
        fitness = add_enum_constant(s, constant, Response, single=True, constraint=all,
                                    description=f'Data needed to calculate the FF-model fitness for {days}d - ' +
                                    'see Response enum')
        set_constant(s, fitness, dumps({'src_owner': short_cls(ImpulseCalculator),
                                        'dest_name': name, 'tau_days': days, 'start': start, 'scale': scale}))

    for days, start, scale in fatigue:
        name = FATIGUE_D % days
        constant = name_constant(name, all)
        responses.append(constant)
        fitness = add_enum_constant(s, constant, Response, single=True, constraint=all,
                                    description=f'Data needed to calculate the FF-model fatigue for {days}d - ' +
                                    'see Response enum')
        set_constant(s, fitness, dumps({'src_owner': short_cls(ImpulseCalculator),
                                        'dest_name': name, 'tau_days': days, 'start': start, 'scale': scale}))

    add_statistics(s, ResponseCalculator, c, owner_in=short_cls(ImpulseCalculator), responses_ref=responses)
