from contextlib import contextmanager
from logging import getLogger, INFO
from urllib.parse import urlsplit

from sqlalchemy import text
from uritools import uriunsplit, urisplit

from .log import log_current_exception
from .names import ADMIN_USER, ADMIN_PASSWD, URI, valid_name, assert_name, USER, PREVIOUS, PASSWD

log = getLogger(__name__)


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
    add_schema(config, schema=previous, extended=True, set_search_path=False)
    q_user = quote(cnxn, user)
    q_previous = quote(cnxn, previous)
    # https://wiki.postgresql.org/wiki/Clone_schema
    with with_log(f'Copying tables to {previous}'):
        for row1 in execute(cnxn, 'select table_name from information_schema.tables WHERE table_schema = :schema',
                            schema=user).fetchall():
            table = row1[0]
            src = f'{q_user}.{quote(cnxn, table)}'
            dst = f'{q_previous}.{quote(cnxn, table)}'
            log.info(f'Creating {dst}')
            execute(cnxn, f'create table {dst} ' 
                          f'(like {src} including constraints including indexes including defaults)')
            log.info(f'Copying {src} to {dst}')
            execute(cnxn, f'insert into {dst} (select * from {src})')
        for row1 in execute(cnxn, 'select table_name from information_schema.tables WHERE table_schema = :schema',
                            schema=user).fetchall():
            table = row1[0]
            src = f'{q_user}.{quote(cnxn, table)}'
            dst = f'{q_previous}.{quote(cnxn, table)}'
            log.info(f'Setting foreign key constraints on {dst}')
            for row2 in execute(cnxn, f'select pg_get_constraintdef(oid), conname from pg_constraint '
                                      f'where contype=\'f\' and conrelid = \'{src}\'::regclass'):
                key, name = row2[0], row2[1]
                key = key.replace(user, previous)
                stmt = f'alter table {dst} add constraint {name} {key}'
                log.debug(key)
                execute(cnxn, stmt)


def remove_schema(config, previous=True):
    if previous and config.args[PREVIOUS]:
        backup_schema(config)
    remove(get_cnxn(config), 'schema', config.args[USER], ' cascade')


def add(cnxn, part, name, stmt, extended=False, **kargs):
    assert_name(name, extended=extended)
    with with_log(f'Adding {part} {name}'):
        stmt = stmt.format(name=quote(cnxn, name))
        log.debug(stmt)
        cnxn.execute(text(stmt), **kargs)


def add_user(config):
    add(get_postgres_cnxn(config), 'user', config.args[USER],
        # note that :xxx invokes sqlalchemy's substitution of parameters in text()
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


def add_schema(config, schema=None, extended=False, set_search_path=True):
    user = config.args[USER]
    assert_name(user)
    schema = schema or user
    assert_name(schema, extended=extended)
    cnxn = get_cnxn(config)
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
    if set_search_path:
        set(cnxn, 'search_path', schema, user, 'alter role {user} set search_path to {schema}')
