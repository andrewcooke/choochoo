from logging import getLogger
from tempfile import TemporaryDirectory

import pandas as pd

from ch2 import activities
from ch2.commands.args import bootstrap_dir, mm, DEV, V, m
from ch2.config.profile.default import default
from ch2.data import activity_statistics, Names as N
from tests import LogTestCase

log = getLogger(__name__)


class TestPower(LogTestCase):

    def test_constant(self):

        with TemporaryDirectory() as f:

            bootstrap_dir(f, m(V), '5', mm(DEV), configurator=default)

            args, sys, db = bootstrap_dir(f, m(V), '5', mm(DEV), 'activities',
                                          'data/test/source/personal/2018-03-04-qdp.fit')
            activities(args, sys, db)

            with db.session_context() as s:
                stats = activity_statistics(s, N.LATITUDE, N.LONGITUDE, N.SPHERICAL_MERCATOR_X,
                                            N.SPHERICAL_MERCATOR_Y, N.DISTANCE, N.ELEVATION, N.SPEED,
                                            N.CADENCE, N.HEART_RATE,
                                            local_time='2018-03-04 07:16:33', activity_group='Bike',
                                            with_timespan=True)
                stats.describe()

                sepn = pd.Series(stats.index).diff().median()  # 7 secs
                start = stats.index.min()  # 2018-03-04 10:16:33+00:00
                finish = stats.index.max()  # 2018-03-04 16:34:51+00:00
                even = pd.DataFrame({'keep': True}, index=pd.date_range(start=start, end=finish, freq=sepn))
                both = stats.join(even, how='outer', sort=True)
                both.interpolate(method='index', limit_area='inside', inplace=True)
                both = both.loc[both['keep'] == True].drop(columns=['keep'])
                both = both.loc[both[N.TIMESPAN_ID].isin(stats[N.TIMESPAN_ID].unique())]
                both.describe()
