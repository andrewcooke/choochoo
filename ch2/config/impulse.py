
from json import dumps

from .database import add_statistics, add_enum_constant, set_constant, name_constant
from ..squeal.types import short_cls
from ..stoats.calculate.heart_rate import HRImpulse, HeartRateCalculator
from ..stoats.calculate.impulse import Response, ImpulseCalculator
from ..stoats.names import HR_IMPULSE, FITNESS, FATIGUE
from ..stoats.read.segment import SegmentReader

FITNESS_CNAME = 'Fitness'
FATIGUE_CNAME = 'Fatigue'


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

    activity_group_constraint = str(activity_group)

    hr_impulse_name = name_constant('HRImpulse', activity_group)
    hr_impulse = add_enum_constant(s, hr_impulse_name, HRImpulse, single=True,
                                   constraint=activity_group_constraint,
                                   description='Data needed to calculate the FF-model impulse from HR zones - ' +
                                               'see HRImpulse enum')
    set_constant(s, hr_impulse, dumps({'dest_name': HR_IMPULSE, 'gamma': 1.0, 'zero': 2, 'max_secs': 60}))

    # 7 and 42 days as for training peaks
    # https://www.trainingpeaks.com/blog/the-science-of-the-performance-manager/
    # 1e-10 as an initial value looks ok on log plot (zero causes numerical issues)

    fitness_name = name_constant(FITNESS_CNAME, activity_group)
    fitness = add_enum_constant(s, fitness_name, Response, single=True, constraint=activity_group_constraint,
                                description='Data needed to calculate the FF-model fitness - see Response enum')
    set_constant(s, fitness, dumps({'src_name': HR_IMPULSE, 'src_owner': short_cls(HeartRateCalculator),
                                    'dest_name': FITNESS, 'tau_days': 42, 'scale': 1, 'start': 1e-10}))

    fatigue_name = name_constant(FATIGUE_CNAME, activity_group)
    fatigue = add_enum_constant(s, fatigue_name, Response, single=True, constraint=activity_group_constraint,
                                description='Data needed to calculate the FF-model fitness - see Response enum')
    set_constant(s, fatigue, dumps({'src_name': HR_IMPULSE, 'src_owner': short_cls(HeartRateCalculator),
                                    'dest_name': FATIGUE, 'tau_days': 7, 'scale': 5, 'start': 1e-10}))

    add_statistics(s, HeartRateCalculator, c, owner_in=short_cls(SegmentReader),
                   impulse=hr_impulse_name)
    add_statistics(s, ImpulseCalculator, c, owner_in=short_cls(HeartRateCalculator),
                   responses=(fitness_name, fatigue_name), impulse=hr_impulse_name)
