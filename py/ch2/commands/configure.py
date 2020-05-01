
from logging import getLogger
from os.path import join, exists
from shutil import rmtree

from .args import no, mm, SUB_COMMAND, CHECK, DATA, CONFIGURE, ACTIVITY_GROUPS, LIST, PROFILE, DIARY, DELETE, FORCE, \
    BASE
from .help import Markdown
from ..config.utils import profiles, get_profile
from ..lib.utils import slow_warning
from ..sql import SystemConstant, ActivityGroup
from ..sql.tables.statistic import StatisticName, StatisticJournal

log = getLogger(__name__)


def configure(args, sys, db):
    '''
## configure

    > ch2 configure load default

Generate a simple initial configuration.

Please see the documentation at http://andrewcooke.github.io/choochoo - you have a lot more options!

    > ch2 configure check --no-config --no-data

Check that the current database is empty.
    '''
    action = args[SUB_COMMAND]
    if action == CHECK:
        check(db, args[no(CONFIGURE)], args[no(DATA)], args[no(ACTIVITY_GROUPS)])
    elif action == LIST:
        list()
    elif action == DELETE:
        delete(sys, args.system_path(), args[FORCE])
    else:
        with db.session_context() as s:
            load(sys, s, args[BASE], args[no(DIARY)], args[PROFILE])


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


def load(sys, s, base, no_diary, profile):
    version = sys.get_constant(SystemConstant.DB_VERSION, none=True)
    if version:
        raise Exception(f'System already configured with version {version}')
    fn, spec = get_profile(profile)
    log.info(f'Loading profile {profile}')
    fn(sys, s, base, no_diary)
    log.info(f'Profile {profile} loaded successfully')


def delete(sys, path, force):
    if not force:
        raise Exception(f'If you really want to delete all your data from {base} add {mm(FORCE)}')
    data = join(path, DATA)
    log.debug(f'Checking {data}')
    if not exists(data):
        raise Exception(f'The directory {data} does not exist')
    version = sys.get_constant(SystemConstant.DB_VERSION, none=True)
    if not version:
        log.info(f'Deleting unconfigured system')
    slow_warning(f'Deleting {path}')
    rmtree(path)

