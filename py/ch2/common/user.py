from logging import getLogger

from sqlalchemy import text
from sqlalchemy.sql import quoted_name

from .names import URI
from .sql import database_really_exists

log = getLogger(__name__)


class ConnectionError(Exception): pass


def make_user_database(config, user, passwd):
    uri = config.args._with(user=user, passwd=passwd)._format(URI)
    if database_really_exists(uri):
        log.warning(f'User {user} can already connect')
        return
    cnxn = config.db.engine.connect()
    if cnxn.execute(text('select 1 from pg_roles where rolname = :user'), user=user).fetchone():
        log.error(f'User already exists but could not connect with supplied password')
        raise ConnectionError()
    log.warning(f'Creating user {user}')
    quser = config.db.engine.dialect.identifier_preparer.quote_identifier(user)
    cnxn.execute(text(f'create role {quser} with login password :passwd'), passwd=passwd)
    log.warning(f'Creating schema {user}')
    cnxn.execute(text(f'create schema {quser} authorization {quser}'))
    log.warning(f'Granting access to {user}')
    cnxn.execute(text(f'alter role {quser} set search_path to {quser}'))
    cnxn.execute(text(f'grant usage on schema {quser} to {quser}'))
    cnxn.execute(text(f'grant insert, select, update, delete on all tables in schema {quser} to {quser}'))
    log.warning(f'Creating tables')
    return config.get_database(uri, user=user, passwd=passwd)

