
from logging import getLogger

from sentinelsat import SentinelAPI
from shapely.geometry import MultiPoint, box

from ..data import Statistics
from ..names import N
from ..pipeline.owners import SegmentReader

log = getLogger(__name__)


def query_activity(s, user, passwd, local_time, margin=0.1):
    df = Statistics(s, activity_journal=local_time).by_name(SegmentReader, N.LATITIUDE, N.LONGITUDE).df
    df = df.dropna()
    footprint = MultiPoint(df.apply(lambda row: (row[Names.LONGITUDE], row[Names.LATITUDE]),
                                    axis='columns')).convex_hull
    minx, miny, maxx, maxy = footprint.bounds
    dx, dy = maxx - minx, maxy - miny
    bbox = box(minx - margin * dx, miny - margin * dy, maxx + margin * dx, maxy + margin * dy)
    api = SentinelAPI(user, passwd, 'https://scihub.copernicus.eu/dhus')
    products = api.query(area=bbox, platformname='Sentinel-2', date=('NOW-1YEAR', 'NOW'),
                         processinglevel='Level-2A', cloudcoverpercentage=(0, 10))
    return api, products, bbox, df
