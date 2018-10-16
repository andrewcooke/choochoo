
import datetime as dt

from ..config.personal import acooke
from ..config.plan.british import twelve_week_improver


def example_config(args, log, db):
    '''
# example-config

    ch2 example-config

This is provided only for testing and demonstration.

The whole damn point of using Choochoo is that you configure it how you need it.

Please see the documentation at http://andrewcooke.github.io/choochoo/index
    '''
    acooke(db)
    plan = twelve_week_improver(dt.date.today())
    plan.create(log, db, sort=1000)

