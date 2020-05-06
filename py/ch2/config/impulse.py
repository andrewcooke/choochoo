from logging import getLogger

from .database import add_statistics, add_enum_constant
from ..names import FITNESS_D, FATIGUE_D, ALL
from ..pipeline.calculate.impulse import HRImpulse, ImpulseCalculator
from ..pipeline.calculate.response import Response, ResponseCalculator
from ..pipeline.read.segment import SegmentReader
from ..sql.types import short_cls

log = getLogger(__name__)

HR_IMPULSE_CNAME = 'HRImpulse'


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

    constant = add_enum_constant(s, HR_IMPULSE_CNAME, HRImpulse,
                                 {'gamma': 2.0, 'zero': 1, 'one': 6, 'max_secs': 60},
                                 single=True, activity_group=activity_group, description='''
Data needed to calculate the FF-model impulse from heart rate zones.
* Gamma is an exponent used to weight the relative importance of hard and easy efforts and should be around 1 (typical range 0.5 to 2).
* Zero defines the lowest heart zone used (so a value of 2 means that a HR zone of 2.0 or less contributes zero impulse).
* One defines the range of heart rate zones used (so a value of 6 means that a HR zone of 6.0 gives a unit impulse per time interval).
* Max_secs is the maximum gap between heart rate measurements (data that exceed this give no impulse).
Once the impulse is calculated it is summed with a decay to find fitness and fatigue
(see Fitness and Fatigue constants). 
''')
    add_statistics(s, ImpulseCalculator, c, owner_in=short_cls(SegmentReader), impulse_ref=constant.name,
                   activity_group=activity_group.name)


def add_responses(s, c, fitness=((42, 1, 1),), fatigue=((7, 1, 5),)):

    responses = []

    for days, start, scale in fitness:
        name = FITNESS_D % days
        log.debug(f'Adding fitness {name}')
        constant = add_enum_constant(s, name, Response,
                                     {'src_owner': short_cls(ImpulseCalculator),
                                      'dest_name': name, 'tau_days': days, 'start': start, 'scale': scale},
                                     single=True, activity_group=ALL, description=f'''
Data needed to calculate the FF-model fitness for {days} days.
* Src_owner is the process that generated the input data (ImpulseCalculator calculates the HR impulses).
* Dest_name is the statistic name where the results are stored.
* Tau_days is the time period (in days) over which the fitness decays.
* Start is the initial fitness value.
* Scale is an arbitrary scale factor (typically used so that fitness and fatigue have comparable values).
''')
        responses.append(constant.name)

    for days, start, scale in fatigue:
        name = FATIGUE_D % days
        log.debug(f'Adding fatigue {name}')
        constant = add_enum_constant(s, name, Response,
                                     {'src_owner': short_cls(ImpulseCalculator),
                                      'dest_name': name, 'tau_days': days, 'start': start, 'scale': scale},
                                     single=True, activity_group=ALL, description=f'''
Data needed to calculate the FF-model fatigue for {days} days.
* Src_owner is the process that generated the input data (ImpulseCalculator calculates the HR impulses).
* Dest_name is the statistic name where the results are stored.
* Tau_days is the time period (in days) over which the fitness decays.
* Start is the initial fitness value.
* Scale is an arbitrary scale factor (typically used so that fitness and fatigue have comparable values).
''')
        responses.append(constant.name)

    add_statistics(s, ResponseCalculator, c, owner_in=short_cls(ImpulseCalculator), responses_ref=responses)
