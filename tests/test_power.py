
import pandas as pd
from tempfile import NamedTemporaryFile
from unittest import TestCase

from ch2 import activities, constants
from ch2.commands.args import bootstrap_file, mm, DEV, FAST, V, m
from ch2.config import default, getLogger
from ch2.data import activity_statistics, LATITUDE, LONGITUDE, SPHERICAL_MERCATOR_X, SPHERICAL_MERCATOR_Y, DISTANCE, \
    ELEVATION, SPEED, CADENCE, HEART_RATE, TIME, TIMESPAN_ID

log = getLogger(__name__)


class TestPower(TestCase):

    def test_constant(self):
        with NamedTemporaryFile() as f:

            bootstrap_file(f, m(V), '5', mm(DEV), configurator=default)

            args, db = bootstrap_file(f, m(V), '5', 'constants', '--set', 'FTHR.%', '154')
            constants(args, db)
            args, db = bootstrap_file(f, m(V), '5', 'constants', 'FTHR.%')
            constants(args, db)
            args, db = bootstrap_file(f, m(V), '5', mm(DEV),
                                           'activities', mm(FAST), 'data/test/source/personal/2018-03-04-qdp.fit')
            activities(args, db)

            with db.session_context() as s:
                stats = activity_statistics(s, LATITUDE, LONGITUDE, SPHERICAL_MERCATOR_X, SPHERICAL_MERCATOR_Y,
                                            DISTANCE, ELEVATION, SPEED, CADENCE, HEART_RATE,
                                            local_time='2018-03-04 07:16:33', activity_group_name='Bike',
                                            with_timespan=True)
                stats.describe()

                sepn = pd.Series(stats.index).diff().median()  # 7 secs
                start = stats.index.min()  # 2018-03-04 10:16:33+00:00
                finish = stats.index.max()  # 2018-03-04 16:34:51+00:00
                even = pd.DataFrame({'keep': True}, index=pd.date_range(start=start, end=finish, freq=sepn))
                both = stats.join(even, how='outer', sort=True)
                both.interpolate(method='index', limit_area='inside', inplace=True)
                both = both.loc[both['keep'] == True].drop(columns=['keep'])
                both = both.loc[both[TIMESPAN_ID].isin(stats[TIMESPAN_ID].unique())]
                both.describe()
