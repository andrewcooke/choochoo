
from logging import getLogger

from .args import QUERY
from ..data import constrained_activities

log = getLogger(__name__)


def search(args, system, db):
    '''
## search

    > ch2 search

This is still in development.
    '''
    query = args[QUERY]
    with db.session_context() as s:
        run_search(s, query)


def run_search(s, query):
    for aj in constrained_activities(s, query):
        print(aj)
