
from tests import LogTestCase

from ch2.data import session, std_health_statistics
from ch2.data.names import REST_HR


class TestHealthBug(LogTestCase):

    def test_health_bug(self):
        '''
        this is only going to work with a database with my data.
        '''
        s = session('-v2')
        df = std_health_statistics(s)
        print(df.describe())
        print(df[REST_HR].describe())
