
from logging import getLogger

from ..config import Config

log = getLogger(__name__)


def default(sys, s, base, no_diary):
    '''
## default

The default configuration with basic activity groups, diary topics and FF parameters.
    '''
    Config(sys, base, no_diary=no_diary).load(s)
