
from .british import twelve_week_improver
from .exponential import exponential_time, exponential_distance
from ..command.args import LIST, PLAN
from ..squeal.database import Database


PLANS = {'british-cycling-12-week-improver': twelve_week_improver,
         'percent-time': exponential_time,
         'percent-distance': exponential_distance}


def list():
    # todo - reformat to width
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
        raise Exception('Unknown plan "%s" (see `ch2 plan --list` for available plans)' % plan)


def add_plan(args, log):
    '''
# add-plan

    ch2 add-plan --list
    ch2 add-plan NAME [values]

Schedule reminders for a given plan.

## Example

    ch2 plan percent-time Run 'w[mon,wed,fri]' 20m 10 2018-07-20 1M

This schedules reminders labelled 'Run' on Mondays, Wednesdays and Fridays of each
week, starting 2018-07-20 and continuing for a month (1M), with times that start
at 20 minutes (20m) and increase each time by 10%.
    '''
    if args[LIST]:
        list()
    elif not args[PLAN]:
        raise Exception('No plan name (see `ch2 plan --list` for available plans)')
    else:
        load(args, log)
