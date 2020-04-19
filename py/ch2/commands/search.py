
from logging import getLogger

from .args import QUERY
from ..data import constrained_activities

log = getLogger(__name__)


def search(args, system, db):
    '''
## search

    > ch2 search QUERY

This searches for activities.

The query syntax is similar to SQL, but element names are statistic names.
The name can include the activity group (start:bike) and SQL wildcards (%fitness).

Negation and NULL values are not supported.

This is still in development.
    '''
    query = args[QUERY]
    with db.session_context() as s:
        run_search(s, query)


def run_search(s, query):
    for aj in constrained_activities(s, query):
        print(aj)
