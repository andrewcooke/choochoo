
from logging import getLogger

from sentinelsat import SentinelAPI
from shapely.geometry import MultiPoint

from ..data import activity_statistics
from ..stoats.names import LATITUDE, LONGITUDE

log = getLogger(__name__)


def query_activity(s, user, passwd, local_time, activity_group_name):
    df = activity_statistics(s, LATITUDE, LONGITUDE, local_time=local_time, activity_group_name=activity_group_name)
    df = df.dropna()
    footprint = MultiPoint(df.apply(lambda row: (row[LONGITUDE], row[LATITUDE]), axis='columns')).convex_hull
    api = SentinelAPI(user, passwd, 'https://scihub.copernicus.eu/dhus')
    products = api.query(area=footprint, platformname='Sentinel-2', date=('NOW-1YEAR', 'NOW'),
                         processinglevel='Level-2A', cloudcoverpercentage=(0, 10))
    return api, products
