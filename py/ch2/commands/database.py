
from logging import getLogger
from os.path import join, exists
from shutil import rmtree

from uritools import urisplit

from .args import no, mm, SUB_COMMAND, CHECK, DATA, DATABASE, ACTIVITY_GROUPS, LIST, PROFILE, DIARY, DELETE, FORCE, \
    BASE, SHOW, DB_VERSION, URI, SQLITE, base_system_path, ACTIVITY
from .help import Markdown
from ..config.utils import profiles, get_profile
from ..lib.utils import slow_warning
from ..sql import SystemConstant, ActivityGroup
from ..sql.database import sqlite_uri
from ..sql.tables.statistic import StatisticName, StatisticJournal

log = getLogger(__name__)


def database(args, sys, db):
    '''
## database

    > ch2 database load (--sqlite|--pgsql|--uri URI) [--delete] PROFILE

Load the initial database schema.

    > ch2 database list

List the available profiles.

    > ch2 database show

Show the current database state.
    '''
    action = args[SUB_COMMAND]
    if action == SHOW:
        show(sys)
    elif action == LIST:
        list()
    else:
        load(sys, args[BASE], args[PROFILE], args[URI], args[DELETE])


def show(sys):
    uri = sys.get_constant(SystemConstant.DB_URI, none=True)
    if uri:
        print(f'{URI}: {uri}')
    else:
        print('no database configured')
    return


def list():
    fmt = Markdown()
    for name in profiles():
        fn, spec = get_profile(name)
        if fn.__doc__:
            fmt.print(fn.__doc__)
        else:
            print(f' ## {name} - lacks docstring\n')


def delete(sys, uri):
    uri_parts = urisplit(uri)
    if uri_parts.scheme == SQLITE:
        log.warning(f'Deleteing {uri_parts.path}')
        rmtree(uri_parts.path)
    else:
        raise Exception(f'Unsupported URI {uri}')
    sys.delete_constant(SystemConstant.DB_URI)


def check_and_delete(sys, delete):
    existing = sys.get_constant(SystemConstant.DB_VERSION, none=True)
    if bool(existing) != delete:
        if existing:
            raise Exception(f'Database already exists {existing} (use {mm(DELETE)})')
        else:
            raise Exception(f'You specified {mm(DELETE)} but no database exists')
    if existing:
        delete(sys, existing)


def create(sys, base, scheme):
    if scheme == SQLITE:
        uri = sqlite_uri(base_system_path(base, subdir=DATA, file=ACTIVITY))
    else:
        raise Exception(f'Unsupported scheme {scheme}')
    log.debug(f'New database at {uri}')
    sys.set_constant(SystemConstant.DB_URI, uri)


def load(sys, base, profile, scheme, delete=False):
    check_and_delete(sys, delete)
    create(sys, base, scheme)
    fn, spec = get_profile(profile)
    log.info(f'Loading profile {profile}')
    db = sys.get_database()
    with db.session_context() as s:
        fn(s, base)
    log.info(f'Profile {profile} loaded successfully')
    sys.set_constant(SystemConstant.DB_VERSION, DB_VERSION)
