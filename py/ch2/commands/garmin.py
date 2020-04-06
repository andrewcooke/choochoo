
from logging import getLogger
from time import sleep

from requests import HTTPError

from .args import DIR, USER, PASS, DATE, FORCE
from ..fit.download.connect import GarminConnect
from ..lib import now, local_time_to_time, time_to_local_time
from ..lib.log import log_current_exception
from ..lib.utils import clean_path
from ..lib.workers import ProgressTree
from ..sql import Constant, SystemConstant
from ..stats.read.monitor import missing_dates

log = getLogger(__name__)

GARMIN_USER = 'Garmin.User'
GARMIN_PASSWORD = 'Garmin.Password'


def garmin(args, sys, db):
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
    dates = [args[DATE]] if args[DATE] else []
    dir = clean_path(DIR) if args[DIR] else None
    with db.session_context() as s:
        run_garmin(sys, s, dir, args[USER], args[PASS], dates, args[FORCE])


def run_garmin(sys, s, dir=None, user=None, password=None, dates=None, force=False, progress=None):

    from .upload import DATA_DIR

    if not dates: dates = list(missing_dates(s, force=force))
    local_progress = ProgressTree(len(dates), parent=progress)

    try:
        if not dates:
            log.info('No missing data to download')
            return

        last = sys.get_constant(SystemConstant.LAST_GARMIN, none=True)
        if last and (now() - local_time_to_time(last)).total_seconds() < 12 * 60 * 60:
            log.info(f'Too soon since previous call ({last}; 12 hours minimum)')
            return
        sys.set_constant(SystemConstant.LAST_GARMIN, time_to_local_time(now()), True)

        old_format = bool(dir)
        dir = dir or Constant.get_single(s, DATA_DIR)
        user = user or Constant.get_single(s, GARMIN_USER)
        password = password or Constant.get_single(s, GARMIN_PASSWORD)
        connect = GarminConnect(log_response=False)
        connect.login(user, password)

        for repeat, date in enumerate(dates):
            if repeat:
                sleep(1)
            log.info('Downloading data for %s' % date)
            try:
                with local_progress.increment_or_complete():
                    connect.get_monitoring_to_fit_file(date, dir, old_format)
            except HTTPError:
                log_current_exception(traceback=False)
                log.info('End of data')
                return

    finally:
        local_progress.complete()

