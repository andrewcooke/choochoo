
from logging import getLogger

from ..config import Config

log = getLogger(__name__)


def default(s, base):
    '''
## default

The default configuration with basic activity groups, diary topics and FF parameters.
    '''
    Config(base).load(s)
