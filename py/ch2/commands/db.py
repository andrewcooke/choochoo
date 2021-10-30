from logging import getLogger

from .args import SUB_COMMAND, LIST, PROFILE, ITEM, USERS, SCHEMAS, DATABASES, PROFILES, ADD, DATABASE, SCHEMA, REMOVE, \
    BACKUP
from ..common.db import add_schema, with_log, remove_schema, remove_database, remove_user, add_database, \
    add_user, list_databases, list_schemas, list_users, backup_schema
from ..common.md import Markdown
from ..common.names import USER
from ..config.profile import get_profile, get_profiles
from ..sql.support import Base

log = getLogger(__name__)


def db(config):
    '''
## db

    > ch2 db list users
    > ch2 db list schemas
    > ch2 db list profiles
    > ch2 db list databases

    > ch2 db add user
    > ch2 db add profile PROFILE
    > ch2 db add database

    > ch2 db remove user
    > ch2 db remove schema
    > ch2 db remove database

### Utilities for managing the database.

This command uses the same configuration parameters, and makes the same assumptions about how the system
works, as other commands.  So creating a database creates a database for the current version, adding a
user adds the current user, etc.

Postgres provides a database cluster at a given address/port.  This contains various users and databases.
To store activity data we use a database for each (minor) release version (eg activity-0-35).
Within any version/database, a user can configure a schema with whatever profile they want.
The schema is named after, and owned by, the user and the user can only see data in the schema they own.

There is no 'db add schema' because the schema is added implicitly when the profile is added;
there is no 'db remove profile' because the profile is removed implicitly when the schema is removed
(a schema contains a profile).

### Note On Backups

When a schema is deleted it is copied to `original_name:previous`.  This is done so that user entries
can be read across when re-installing the same version.  That is all.  There is no greater backup
functionality implied or supported.  Backup the database separately if it is important.
'''
    args = config.args
    action, item = args[SUB_COMMAND], args[ITEM]
    {LIST: {USERS: list_users,
            SCHEMAS: list_schemas,
            DATABASES: list_databases,
            PROFILES: list_profiles},
     ADD: {USER: add_user,
           DATABASE: add_database,
           PROFILE: add_profile},
     BACKUP: {SCHEMA: backup_schema},
     REMOVE: {USER: remove_user,
              DATABASE: remove_database,
              SCHEMA: remove_schema}}[action][item](config)


def list_profiles(config):
    fmt = Markdown()
    for name in get_profiles():
        fn, spec = get_profile(name)
        if fn.__doc__:
            fmt.print(fn.__doc__)
        else:
            print(f' ## {name} - lacks docstring\n')


def add_profile(config):
    add_schema(config)
    with with_log('Creating tables'):
        Base.metadata.create_all(config.db.engine)
    profile = config.args[PROFILE]
    fn, spec = get_profile(profile)
    with with_log(f'Loading profile {profile}'):
        fn(config)
