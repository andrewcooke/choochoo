
import pdb

from .british import twelve_week_improver
from ..args import LIST, PLAN
from ..log import make_log
from ..squeal.database import Database


PLANS = {'british-cycling-12-week-improver': twelve_week_improver}


def list():
    for name, plan in PLANS.items():
        print('  %s:' % name)
        print(plan.__doc__)


def load(args):
    log = make_log(args)
    db = Database(args, log)
    plan = args[PLAN][0]
    extra = args[PLAN][1:]
    if plan in PLANS:
        with db.session_context() as session:
            PLANS[plan](*extra).create(log, session)
    else:
        raise Exception('Unknown plan "%s"' % plan)


def main(args):
    if args[LIST]:
        list()
    elif not args[PLAN]:
        raise Exception('No plan name')
    else:
        load(args)
