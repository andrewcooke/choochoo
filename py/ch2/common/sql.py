from sqlalchemy_utils import database_exists

from .log import log_current_exception


def database_really_exists(uri):
    try:
        return database_exists(uri)
    except Exception:
        log_current_exception(traceback=False)
        return False
