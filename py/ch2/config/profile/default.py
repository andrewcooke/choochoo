
from logging import getLogger

from ..config import Config

log = getLogger(__name__)


def default(sys, s, no_diary):
    '''
## default

The default configuration with basic activity groups, diary topics and FF parameters.
    '''
    Config(sys, no_diary=no_diary).load(s)
