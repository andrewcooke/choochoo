
from logging import getLogger

from ..config import Config

log = getLogger(__name__)


def default(s, data):
    '''
## default

The default configuration with basic activity groups, diary topics and FF parameters.
    '''
    Config(data).load(s)
