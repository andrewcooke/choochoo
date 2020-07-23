from contextlib import contextmanager
from logging import getLogger, INFO
from urllib.parse import urlsplit

from sqlalchemy import text
from uritools import urisplit, uriunsplit

from .args import SUB_COMMAND, LIST, PROFILE, ITEM, USERS, SCHEMAS, DATABASES, PROFILES, ADD, DATABASE, SCHEMA, REMOVE
from .help import Markdown
from ..common.log import log_current_exception
from ..common.names import URI, USER, ADMIN_USER, ADMIN_PASSWD, valid_name, assert_name, PASSWD, PREVIOUS
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
     REMOVE: {USER: remove_user,
              DATABASE: remove_database,
              SCHEMA: remove_schema}}[action][item](config)


@contextmanager
def with_log(msg):
    log.warning(msg)
    try:
        yield
        log.info(msg.replace('ing ', 'ed '))
    except:
        log_current_exception(exception_level=INFO, first=True)
        msg = 'Error ' + msg[0].lower() + msg[1:]
        raise Exception(msg)


def get_cnxn(config, **kargs):
    return config.get_database(user=config.args[ADMIN_USER], passwd=config.args[ADMIN_PASSWD], **kargs) \
        .engine.connect()


def get_postgres_cnxn(config):
    return get_cnxn(config, uri=uriunsplit(urisplit(config.args[URI])._replace(path='/postgres')))


def print_query(cnxn, query, extended=False):
    log.debug(query)
    for row in cnxn.execute(text(query)).fetchall():
        name = row[0]
        if valid_name(name, extended=extended):
            print(name)


def list_users(config):
    print_query(get_postgres_cnxn(config), 'select rolname from pg_roles')


def list_schemas(config):
    print_query(get_cnxn(config), 'select nspname from pg_namespace', extended=True)


def list_databases(config):
    print_query(get_postgres_cnxn(config), 'select datname from pg_database')


def list_profiles(config):
    fmt = Markdown()
    for name in get_profiles():
        fn, spec = get_profile(name)
        if fn.__doc__:
            fmt.print(fn.__doc__)
        else:
            print(f' ## {name} - lacks docstring\n')


def quote(cnxn, name):
    # not really needed as we have already validated the name, but let's be as secure as possible
    return cnxn.engine.dialect.identifier_preparer.quote_identifier(name)


def remove(cnxn, part, name, extra='', extended=False):
    name = assert_name(name, extended=extended)
    with with_log(f'Removing {part} {name}'):
        stmt = f'drop {part} {quote(cnxn, name)}' + extra
        log.debug(stmt)
        cnxn.execute(text(stmt))


def remove_user(config):
    remove(get_postgres_cnxn(config), 'role', config.args[USER])


def remove_database(config):
    remove(get_postgres_cnxn(config).execution_options(isolation_level='AUTOCOMMIT'),
           'database',
           urlsplit(config.args._format(URI)).path[1:])


def execute(cnxn, stmt, **kargs):
    log.debug(f'Executing {stmt} with {kargs}')
    return cnxn.execute(text(stmt), **kargs)


def test_schema(cnxn, schema):
    return bool(execute(cnxn, 'select 1 from pg_namespace where nspname = :schema', schema=schema).first())


def backup_schema(config):
    user = config.args[USER]
    assert_name(user)
    previous = user + ':' + PREVIOUS
    cnxn = get_cnxn(config)
    if test_schema(cnxn, previous):
        remove(cnxn, 'schema', previous, ' cascade', extended=True)
    add_schema(cnxn, user, previous, extended=True)
    # https://wiki.postgresql.org/wiki/Clone_schema
    with with_log(f'Copying tables to {previous}'):
        for row in execute(cnxn, 'select table_name from information_schema.tables WHERE table_schema = :schema',
                           schema=user).fetchall():
            table = row[0]
            execute(cnxn, f'create table {quote(cnxn, previous)}.{quote(cnxn, table)} '
                          f'(like {quote(cnxn, user)}.{quote(cnxn, table)} '
                          f'including constraints including indexes including defaults)')
            execute(cnxn, f'insert into {quote(cnxn, previous)}.{quote(cnxn, table)} '
                          f'(select * from {quote(cnxn, user)}.{quote(cnxn, table)})')


def remove_schema(config, backup=True):
    if backup:
        backup_schema(config)
    # todo - will this work with the user?  maybe need to use postgres but connect to this database
    remove(get_cnxn(config), 'schema', config.args[USER], ' cascade')


def add(cnxn, part, name, stmt, extended=False, **kargs):
    assert_name(name, extended=extended)
    with with_log(f'Adding {part} {name}'):
        stmt = stmt.format(name=quote(cnxn, name))
        log.debug(stmt)
        cnxn.execute(text(stmt), **kargs)


def add_user(config):
    add(get_postgres_cnxn(config), 'user', config.args[USER],
        'create role {name} with login password :passwd',
        passwd=config.args[PASSWD])


def add_database(config):
    cnxn = get_postgres_cnxn(config).execution_options(isolation_level='AUTOCOMMIT')
    add(cnxn, 'database', urlsplit(config.args._format(URI)).path[1:],
        f'create database {{name}} with owner {quote(cnxn, config.args[USER])}')


def set(cnxn, part, schema, user, stmt, extended=False):
    assert_name(schema, extended=extended)
    assert_name(user)
    with with_log(f'Setting {part} on {schema} for {user}'):
        stmt = stmt.format(schema=quote(cnxn, schema), user=quote(cnxn, user))
        log.debug(stmt)
        cnxn.execute(text(stmt))


def add_schema(cnxn, user, schema, extended=False):
    # search_path is set separately because we don't include the backup
    assert_name(user)
    assert_name(schema,
                extended=extended)
    add(cnxn, 'schema', schema, f'create schema {{name}} authorization {quote(cnxn, user)}',
        extended=extended)
    set(cnxn, 'usage', schema, user, 'grant usage on schema {schema} to {user}',
        extended=extended)
    set(cnxn, 'permissions', schema, user,
        'grant insert, select, update, delete on all tables in schema {schema} to {user}',
        extended=extended)
    set(cnxn, 'permissions', schema, user,
        'alter default privileges in schema {schema} grant insert, select, update, delete on tables to {user}',
        extended=extended)


def add_profile(config):
    cnxn = get_cnxn(config)
    user = config.args[USER]
    assert_name(user)
    add_schema(cnxn, user, user)
    with with_log('Setting search_path'):
        set(cnxn, 'search_path', user, user, 'alter role {user} set search_path to {schema}')
    with with_log('Creating tables'):
        Base.metadata.create_all(config.db.engine)
    profile = config.args[PROFILE]
    fn, spec = get_profile(profile)
    with with_log(f'Loading profile {profile}'):
        fn(config)




# todo - web needs moving to above --------------
#
#
# def show(config):
#     uri = config.get_uri()
#     if uri:
#         print(f'{URI}:     {uri}')
#         print(f'version: {DB_VERSION}')
#         print(f'exists:  {database_really_exists(uri)}')
#     else:
#         print('no database configured')
#     return
#
#
# def list():
#     fmt = Markdown()
#     for name in profiles():
#         fn, spec = get_profile(name)
#         if fn.__doc__:
#             fmt.print(fn.__doc__)
#         else:
#             print(f' ## {name} - lacks docstring\n')
#
#
# def delete_and_check(config, force=False):
#     # the database exists because it's created when we connect, but does it have a schema?
#     uri = config.get_uri()
#     if force:
#         drop_database(uri)
#     config.reset()
#     if database_exists(uri) and not config.db.no_data():
#         raise Exception(f'Data exist at {uri} (use {mm(FORCE)}?)')
#
#
# def write(uri, profile, config):
#     fn, spec = get_profile(profile)
#     log.info(f'Loading profile {profile}')
#     db = config.get_database(uri)  # writes schema automatically
#     with db.session_context() as s:
#         fn(s, config)  # todo - no need for s
#     log.info(f'Profile {profile} loaded successfully')
#
#
# def load(config, profile, force=False):
#     uri = config.get_uri()
#     delete_and_check(config, force=force)
#     write(uri, profile, config)
