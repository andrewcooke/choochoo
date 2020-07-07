from logging import getLogger
from tempfile import TemporaryDirectory

import pandas as pd

from ch2.commands.args import DEV, V, bootstrap_db, BASE
from ch2.commands.read import read
from ch2.common.args import mm, m
from ch2.config.profile.default import default
from ch2.data import Names as N, Statistics
from ch2.pipeline.read import SegmentReader
from tests import LogTestCase, random_test_user

log = getLogger(__name__)


class TestPower(LogTestCase):

    def test_constant(self):

        user = random_test_user()
        with TemporaryDirectory() as f:

            bootstrap_db(user, m(V), '5', mm(DEV), configurator=default)

            args, data = bootstrap_db(user, mm(BASE), f, m(V), '5', mm(DEV), 'read',
                                       'data/test/source/personal/2018-03-04-qdp.fit')
            read(args, data)

            with data.db.session_context() as s:
                stats = Statistics(s, activity_journal='2018-03-04 07:16:33', with_timespan=True). \
                    by_name(SegmentReader, N.LATITUDE, N.LONGITUDE, N.SPHERICAL_MERCATOR_X,
                            N.SPHERICAL_MERCATOR_Y, N.DISTANCE, N.ELEVATION, N.SPEED, N.CADENCE, N.HEART_RATE).df
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
