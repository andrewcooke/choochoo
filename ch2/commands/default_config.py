
from logging import getLogger

from .args import DIARY, no
from ..config import default
from ..squeal.tables.activity import ActivityGroup
from ..squeal.tables.statistic import StatisticName

log = getLogger(__name__)


def default_config(args, db):
    '''
## default-config

    > ch2 default-config

Generate a simple initial configuration.

Please see the documentation at http://andrewcooke.github.io/choochoo
    '''
    no_diary = args[no(DIARY)]
    with db.session_context() as s:
        if not no_diary and s.query(StatisticName).count():
            raise Exception('The database already contains StatisticName entries')
        if s.query(ActivityGroup).count():
            raise Exception('The database already contains ActivityGroup entries')
    default(db, no_diary=no_diary)
