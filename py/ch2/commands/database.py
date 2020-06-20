
from logging import getLogger
from os import unlink

from sqlalchemy_utils import create_database, drop_database, database_exists
from uritools import urisplit

from .args import mm, SUB_COMMAND, LIST, PROFILE, BASE, SHOW, DB_VERSION, URI, SQLITE, POSTGRESQL, \
    FORCE, DELETE
from .help import Markdown
from ..config.utils import profiles, get_profile
from ..lib import log_current_exception
from ..lib.utils import clean_path
from ..sql import SystemConstant
from ..sql.database import sqlite_uri, postgresql_uri

log = getLogger(__name__)


def database(args, data):
    '''
## database

    > ch2 database load (--sqlite|--pgsql|--uri URI) [--delete] PROFILE

Load the initial database schema.

    > ch2 database list

List the available profiles.

    > ch2 database show

Show the current database state.

    > ch2 database delete

Delete the current database.
    '''
    action = args[SUB_COMMAND]
    if action == SHOW:
        show(data.sys)
    elif action == LIST:
        list()
    elif action == DELETE:
        uri = args[URI] or sys.get_constant(SystemConstant.DB_URI, none=True)
        if not uri: raise Exception('No current database is defined')
        delete(uri, data.sys)
    else:
        load(data.sys, args[BASE], args[PROFILE], args[URI], args[FORCE])


def database_really_exists(uri):
    try:
        return database_exists(uri)
    except Exception:
        log_current_exception(traceback=False)
        return False


def show(sys):
    uri = sys.get_constant(SystemConstant.DB_URI, none=True)
    version = sys.get_constant(SystemConstant.DB_VERSION, none=True)
    if uri:
        print(f'{URI}:     {uri}')
        print(f'version: {version}')
        print(f'exists:  {database_really_exists(uri)}')
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


def delete_current(sys):
    delete(sys.get_constant(SystemConstant.DB_URI), sys)


def delete(uri, sys):
    try:
        if database_exists(uri):
            log.debug(f'Deleting database at {uri}')
            uri_parts = urisplit(uri)
            if uri_parts.scheme == SQLITE:
                path = clean_path(uri_parts.path)
                log.warning(f'Deleting {path}')
                unlink(path)
            elif uri_parts.scheme == POSTGRESQL:
                drop_database(uri)
            else:
                raise Exception(f'Unsupported URI {uri}')
        else:
            log.warning(f'No database at {uri} (so not deleting)')
    finally:
        sys.delete_constant(SystemConstant.DB_URI)
        sys.delete_constant(SystemConstant.DB_VERSION)


def delete_and_check(uri, force, sys):
    if force: delete(uri, sys)
    if database_exists(uri):
        raise Exception(f'A schema exists at {uri} (use {mm(FORCE)}?)')


def write(uri, profile, sys, base):
    fn, spec = get_profile(profile)
    log.info(f'Loading profile {profile}')
    db = sys.get_database(uri)  # writes schema automatically
    with db.session_context() as s:
        fn(s, base)
    log.info(f'Profile {profile} loaded successfully')
    sys.set_constant(SystemConstant.DB_URI, uri, force=True)
    sys.set_constant(SystemConstant.DB_VERSION, DB_VERSION, force=True)


def make_uri(base, scheme_or_uri):
    if scheme_or_uri == SQLITE:
        uri = sqlite_uri(base)
    elif scheme_or_uri == POSTGRESQL:
        uri = postgresql_uri()
    else:
        uri = scheme_or_uri
    log.debug(f'Using URI {uri}')
    return uri


def create(uri):
    log.debug(f'Creating database at {uri}')
    create_database(uri)


def load(sys, base, profile, scheme_or_uri, force=False):
    uri = make_uri(base, scheme_or_uri)
    delete_and_check(uri, force, sys)
    create(uri)
    write(uri, profile, sys, base)
