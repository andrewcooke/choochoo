
from logging import getLogger
from time import sleep

from .args import DIR, USER, PASS, DATE
from ..fit.download.connect import GarminConnect
from ..stoats.read.monitor import missing_dates

log = getLogger(__name__)


def garmin(args, db):
    '''
## garmin

    > ch2 garmin --user USER --pass PASSWORD DIR

Download recent monitor data to the given directory.

    > ch2 garmin --user USER --pass PASSWORD --date DATE DIR

Download monitor data for the given date.

Note that this cannot be used to download more than 10 days of data.
For bulk downloads use
https://www.garmin.com/en-US/account/datamanagement/
    '''
    dir, user, password, date = args.dir(DIR, rooted=False), args[USER], args[PASS], args[DATE]
    if date:
        dates = [date]
    else:
        # do this first to avoid login if not needed
        with db.session_context() as s:
            dates = list(missing_dates(s))
    if dates:
        connect = GarminConnect(log_response=False)
        connect.login(user, password)
        for repeat, date in enumerate(dates):
            if repeat:
                sleep(1)
            log.info('Downloading data for %s' % date)
            connect.get_monitoring_to_fit_file(date, dir)
