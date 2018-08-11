
from .british import twelve_week_improver
from .exponential import exponential_time, exponential_distance
from ..args import LIST, PLAN
from ..squeal.database import Database


PLANS = {'british-cycling-12-week-improver': twelve_week_improver,
         'percent-time': exponential_time,
         'percent-distance': exponential_distance}


def list():
    for name, plan in sorted(PLANS.items()):
        print('\n  %s:' % name)
        print(plan.__doc__)


def load(args, log):
    db = Database(args, log)
    plan = args[PLAN][0]
    extra = args[PLAN][1:]
    if plan in PLANS:
        with db.session_context() as session:
            PLANS[plan](*extra).create(log, session)
    else:
        raise Exception('Unknown plan "%s"' % plan)


def plan(args, log):
    if args[LIST]:
        list()
    elif not args[PLAN]:
        raise Exception('No plan name')
    else:
        load(args, log)
