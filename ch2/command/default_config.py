
from .args import NO_DIARY
from ..config import default


def default_config(args, log, db):
    '''
## default-config

    > ch2 default-config

Generate a simple initial configuration.

Please see the documentation at http://andrewcooke.github.io/choochoo
    '''
    default(db, no_diary=args[NO_DIARY])
