
from .config.database import Config
from .config.default import default
from .squeal.database import Database


def default_config(args, log):
    '''
# default-config

THis is provided only for testing and demonstration.

The whole damn point of using Choochoo is that you configure it how you need it.
Please see the documentation.
    '''
    db = Database(args, log)
    config = Config(log, db)
    default(config)
