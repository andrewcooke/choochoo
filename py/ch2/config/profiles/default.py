
from logging import getLogger

from ..profile import Profile

log = getLogger(__name__)


def default(config):
    '''
## default

The default configuration with basic activity groups, diary topics and FF parameters.
    '''
    Profile(config).load()
