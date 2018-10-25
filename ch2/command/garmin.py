
from .args import DIR, USER, PASS, DATE
from ..fit.download.connect import GarminConnect
from ..stoats.read.monitor import missing_dates


def garmin(args, log, db):
    '''
# garmin

    ch2 garmin --user USER --pass PASSWORD DIR

    ch2 garmin --user USER --pass PASSWORD --date DATE DIR

    '''
    dir, user, password, date = args.dir(DIR, rooted=False), args[USER], args[PASS], args[DATE]
    connect = GarminConnect(log, log_response=False)
    connect.login(user, password)
    if date:
        connect.get_monitoring_to_fit_file(date, dir)
    else:
        with db.session_context() as s:
            for date in missing_dates(s):
                connect.get_monitoring_to_fit_file(date, dir)
