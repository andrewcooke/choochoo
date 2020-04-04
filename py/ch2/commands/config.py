
from logging import getLogger

from .args import no, SUB_COMMAND, CHECK, DATA, CONFIG, ACTIVITY_GROUPS, LIST, PROFILE
from ..commands.help import Markdown
from ..config import ActivityGroup
from ..config.utils import profiles, get_profile
from ..sql.tables.statistic import StatisticName, StatisticJournal

log = getLogger(__name__)


def config(args, system, db):
    '''
## config

    > ch2 config load default

Generate a simple initial configuration.

Please see the documentation at http://andrewcooke.github.io/choochoo - you have a lot more options!

    > ch2 config check --no-config --no-data

Check that the current database is empty.
    '''
    action = args[SUB_COMMAND]
    if action == CHECK:
        check(db, args[no(CONFIG)], args[no(DATA)], args[no(ACTIVITY_GROUPS)])
    elif action == LIST:
        list()
    else:
        load(system, db, args, args[PROFILE])


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


def list():
    fmt = Markdown()
    for name in profiles():
        fn, spec = get_profile(name)
        if fn.__doc__:
            fmt.print(fn.__doc__)
        else:
            print(f' ## {name} - lacks docstring\n')


def load(sys, db, args, profile):
    fn, spec = get_profile(profile)
    fn(sys, db, args)

