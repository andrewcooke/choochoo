from json import dumps
from logging import getLogger

from .database import add_statistics, add_enum_constant, set_constant, name_constant
from ..sql import ActivityGroup
from ..sql.types import short_cls
from ..stats.calculate.impulse import HRImpulse, ImpulseCalculator
from ..stats.calculate.response import Response, ResponseCalculator
from ..stats.names import FITNESS_D, FATIGUE_D, ALL
from ..stats.read.segment import SegmentReader

log = getLogger(__name__)


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
    add_enum_constant(s, hr_impulse_name, HRImpulse,
                      {'gamma': 2.0, 'zero': 1, 'one': 6, 'max_secs': 60},
                      single=True, constraint=activity_group, description='''
Data needed to calculate the FF-model impulse from heart rate zones.
* Gamma is an exponent used to weight the relative importance of hard and easy efforts and should be around 1 (typical range 0.5 to 2).
* Zero defines the lowest heart zone used (so a value of 2 means that a HR zone of 2.0 or less contributes zero impulse).
* One defines the range of heart rate zones used (so a value of 6 means that a HR zone of 6.0 gives a unit impulse per time interval).
* Max_secs is the maximum gap between heart rate measurements (data that exceed this give no impulse).
Once the impulse is calculated it is summed with a decay to find fitness and fatigue
(see Fitness and Fatigue constants). 
''')
    add_statistics(s, ImpulseCalculator, c, owner_in=short_cls(SegmentReader), impulse_ref=hr_impulse_name,
                   activity_group_name=activity_group.name)


def add_responses(s, c, fitness=((42, 1, 1),), fatigue=((7, 1, 5),)):
    responses = []
    all = ActivityGroup.from_name(s, ALL)

    for days, start, scale in fitness:
        name = FITNESS_D % days
        constant = name_constant(name, all)
        responses.append(constant)
        log.debug(f'Adding fitness {name}')
        add_enum_constant(s, constant, Response,
                          {'src_owner': short_cls(ImpulseCalculator),
                           'dest_name': name, 'tau_days': days, 'start': start, 'scale': scale},
                          single=True, constraint=all, description=f'''
Data needed to calculate the FF-model fitness for {days} days.
* Src_owner is the process that generated the input data (ImpulseCalculator calculates the HR impulses).
* Dest_name is the statistic name where the results are stored.
* Tau_days is the time period (in days) over which the fitness decays.
* Start is the initial fitness value.
* Scale is an arbitrary scale factor (typically used so that fitness and fatigue have comparable values).
''')

    for days, start, scale in fatigue:
        name = FATIGUE_D % days
        constant = name_constant(name, all)
        responses.append(constant)
        log.debug(f'Adding fatigue {name}')
        add_enum_constant(s, constant, Response,
                          {'src_owner': short_cls(ImpulseCalculator),
                           'dest_name': name, 'tau_days': days, 'start': start, 'scale': scale},
                          single=True, constraint=all, description=f'''
Data needed to calculate the FF-model fatigue for {days} days.
* Src_owner is the process that generated the input data (ImpulseCalculator calculates the HR impulses).
* Dest_name is the statistic name where the results are stored.
* Tau_days is the time period (in days) over which the fitness decays.
* Start is the initial fitness value.
* Scale is an arbitrary scale factor (typically used so that fitness and fatigue have comparable values).
''')
    add_statistics(s, ResponseCalculator, c, owner_in=short_cls(ImpulseCalculator), responses_ref=responses)
