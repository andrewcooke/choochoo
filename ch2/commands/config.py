
from logging import getLogger

from .args import DIARY, no, SUB_COMMAND, DEFAULT, CHECK, DATA, CONFIG, ACTIVITY_GROUPS
from ..config import default, ActivityGroup
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
        no_diary = args[no(DIARY)]
        check(db, not no_diary, not no_diary, True)
        default(db, no_diary=no_diary)
    elif action == CHECK:
        check(db, args[no(CONFIG)], args[no(DATA)], args[no(ACTIVITY_GROUPS)])


def check(db, config, data, activity_groups):
    with db.session_context() as s:
        if config:
            if s.query(StatisticName).count():
                raise Exception('The database already contains StatisticName entries')
        if data:
            if s.query(StatisticJournal).count():
                raise Exception('The database already contains StatisticJournal entries')
        if activity_groups:
            if s.query(ActivityGroup).count():
                raise Exception('The database already contains ActivityGroup entries')
