from logging import getLogger

from sqlalchemy import text

from .db import add_user, add_schema
from .names import URI
from .sql import database_really_exists

log = getLogger(__name__)


class ConnectionError(Exception): pass


def make_user_database(config, user, passwd):

    # this does not create tables, since those are not common to multiple projects

    user_config = config._with(user=user, passwd=passwd)
    user_uri = user_config.args._format(URI)

    if database_really_exists(user_uri):
        log.warning(f'User {user} can already connect')
        return

    cnxn = config.db.engine.connect()
    if cnxn.execute(text('select 1 from pg_roles where rolname = :user'), user=user).fetchone():
        raise ConnectionError(f'User already exists but could not connect with supplied password')

    add_user(user_config)
    add_schema(user_config)
    return user_config
