
from ..database import add_read_and_calculate
from ..profile import Profile
from ...pipeline.read.garmin import GarminReader
from ...pipeline.read.monitor import MonitorReader
from ...pipeline.read.segment import SegmentReader
from ...sql.types import short_cls


def garmin(config):
    '''
## garmin

This extends the default configuration with download of monitor data from Garmin.

It requires the user and password to be defined as constants.
    '''
    Garmin(config).load()


class Garmin(Profile):

    def _load_read_pipeline(self, s):
        sport_to_activity = self._sport_to_activity()
        record_to_db = self._record_to_db()
        add_read_and_calculate(s, SegmentReader, owner_out=short_cls(SegmentReader),
                               sport_to_activity=sport_to_activity, record_to_db=record_to_db)
        monitor_reader = add_read_and_calculate(s, MonitorReader)
        # add these, chained so that we load available data (know what is missing),
        # download new data, and load new data
        garmin_reader = add_read_and_calculate(s, GarminReader, blocked_by=[monitor_reader])
        # this force overrides force=True from the command line
        # (which is applied on the first invocation above)
        add_read_and_calculate(s, MonitorReader, blocked_by=[garmin_reader], force=False)
