
import pandas as pd

from ..squeal.database import connect
from ..squeal import ActivityJournal
from ..squeal.types import short_cls
from ..stoats.read.segment import SegmentImporter
from ..stoats.waypoint import WaypointReader


LOG = [None]


def df(query):
    # https://stackoverflow.com/questions/29525808/sqlalchemy-orm-conversion-to-pandas-dataframe
    return pd.read_sql(query.statement, query.session.bind)


def session(*args):
    ns, log, db = connect(args)
    LOG[0] = log
    return db.session()


def log():
    if not LOG[0]:
        raise Exception('Create session first')
    return LOG[0]


def waypoints(s, activity_journal_id, *statistics, owner=short_cls(SegmentImporter)):
    names = dict((statistic, statistic) for statistic in statistics)
    ajournal = s.query(ActivityJournal).filter(ActivityJournal.id == activity_journal_id).one()
    return pd.DataFrame(WaypointReader(log(), with_timespan=False).read(s, ajournal, names, owner))
