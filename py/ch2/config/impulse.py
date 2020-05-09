from logging import getLogger

from .database import add_statistics, add_enum_constant
from ..names import Titles, Names
from ..pipeline.calculate.impulse import HRImpulse, ImpulseCalculator
from ..pipeline.calculate.response import Response, ResponseCalculator
from ..pipeline.read.segment import SegmentReader
from ..sql import ActivityGroup
from ..sql.types import short_cls

'''
individual impulse calculations are each configured by a separate constant and associated with a 
separate pipeline instance that does the work.  they are grouped by 'prefix' and specific to an
activity group.  so within a prefix there should be no more than one impulse for each group.

the pipeline class generates impulses named by the prefix + the constant.  so the configuration 
for any impulse can be traced back.

for each named impulse there are two statistics - one in the given activity group and one in ALL.

the response calculator combines impulses from all statistics with a given prefix using the data in ALL.
for efficiency a single pipeline instance s used for all responses with a given prefix (so the 
pipeline config is a list of constant names rather than the single name used for impulses).

as with impulses, the responses are named by prefix and constant.   
'''

log = getLogger(__name__)


def add_impulse(s, c, activity_group, gamma=2, zero=1, one=6, max_secs=60,
                title=Titles.HR_IMPULSE_10, prefix=Names.DEFAULT):
    '''
    Add configuration for a fitness/fatigue impulse model based on HR zones.
    '''
    if isinstance(activity_group, ActivityGroup):
        activity_group = activity_group.name
    if activity_group == ActivityGroup.ALL:
        raise Exception(f'Impulse must be defined for a specific group (not {ActivityGroup.ALL})')
    constant = add_enum_constant(s, title, HRImpulse,
                                 {'title': title, 'gamma': 2.0, 'zero': 1, 'one': 6, 'max_secs': 60},
                                 single=True, activity_group=activity_group, description='''
Data needed to calculate the FF-model impulse from heart rate zones.
* Gamma is an exponent used to weight the relative importance of hard and easy efforts and should be around 1 (typical range 0.5 to 2).
* Zero defines the lowest heart zone used (so a value of 2 means that a HR zone of 2.0 or less contributes zero impulse).
* One defines the range of heart rate zones used (so a value of 6 means that a HR zone of 6.0 gives a unit impulse per time interval).
* Max_secs is the maximum gap between heart rate measurements (data that exceed this give no impulse).
Once the impulse is calculated it is summed with a decay to find fitness and fatigue
(see Fitness and Fatigue constants). 
''')
    add_statistics(s, ImpulseCalculator, c, owner_in=short_cls(SegmentReader),
                   impulse_constant=constant.name, prefix=prefix,
                   activity_group=activity_group)


def add_responses(s, c, responses=((42, 1, 1, Titles.FITNESS_D % 42, 'fitness'),
                                   (7, 1, 5, Titles.FATIGUE_D % 7, 'fatigue')),
                  owner_in=ImpulseCalculator, prefix=Names.DEFAULT):
    '''
    Add configuration for a fitness/fatigue response model based on pre-calculated impulses.
    '''
    constants = [add_enum_constant(s, title, Response,
                                   {'src_owner': short_cls(ImpulseCalculator),
                                    'title': title, 'tau_days': days, 'start': start, 'scale': scale},
                                   single=True, description=f'''
Data needed to calculate the FF-model {label} for {days} days.
* Src_owner is the process that generated the input data (ImpulseCalculator calculates the HR impulses).
* Title is the statistic title for display the results.
* Tau_days is the time period (in days) over which the fitness decays.
* Start is the initial fitness value.
* Scale is an arbitrary scale factor (typically used so that fitness and fatigue have comparable values).
''') for (days, start, scale, title, label) in responses]
    add_statistics(s, ResponseCalculator, c,
                   owner_in=short_cls(owner_in), prefix=prefix,
                   response_constants=[constant.name for constant in constants])
