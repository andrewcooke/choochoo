
from logging import getLogger

from .args import DIARY, no, SUB_COMMAND, DEFAULT, CHECK, DATA, CONFIG
from ..config import default
from ..squeal.tables.statistic import StatisticName, StatisticJournal

log = getLogger(__name__)


def config(args, db):
    '''
## config

    > ch2 config default

Generate a simple initial configuration.

Please see the documentation at http://andrewcooke.github.io/choochoo - you have a lot more options!

    > ch2 config check --no-config --no-data

Check that the current database is empty.
    '''
    action = args[SUB_COMMAND]
    if action == DEFAULT:
        check(db, True, True)
        default(db, no_diary=args[no(DIARY)])
    elif action == CHECK:
        check(db, args[no(CONFIG)], args[no(DATA)])


def check(db, config, data):
    with db.session_context() as s:
        if config:
            if s.query(StatisticName).count():
                raise Exception('The database already contains StatisticName entries')
        if data:
            if s.query(StatisticJournal).count():
                raise Exception('The database already contains StatisticJournal entries')
