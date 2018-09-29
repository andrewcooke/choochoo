
import datetime as dt

from .args import FTHR, DATE
from .lib.date import parse_date
from .squeal.database import Database


def add_fthr(args, log):
    '''
# add-fthr

    ch2 add-fthr FTHR [DATE]

Define heart rate zones using the British Cycling calculator (roughly) from the given date (default today).
    '''
    db = Database(args, log)
    fthr = args[FTHR][0]
    if args[DATE]:
        date = parse_date(args[DATE])
    else:
        date = dt.date()
    with db.session_context() as session:
        zones = HeartRateZones(date=date, basis='FTHR %d (British Cycling)' % fthr)
        session.add(zones)
        for pc in (68, 83, 94, 105, 121):
            HeartRateZone(heart_rate_zones=zones, upper_limit=int(0.5 + pc * fthr / 100.0))

