
from .args import NO_DIARY
from ..config import default
from ..squeal.tables.statistic import StatisticName


def default_config(args, log, db):
    '''
## default-config

    > ch2 default-config

Generate a simple initial configuration.

Please see the documentation at http://andrewcooke.github.io/choochoo
    '''
    with db.session_context() as s:
        if s.query(StatisticName).count():
            raise Exception('The database already contains StatisticName entries')
    default(log, db, no_diary=args[NO_DIARY])
