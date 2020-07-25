from logging import getLogger
from time import sleep

from requests import HTTPError

from .monitor import missing_dates
from ..pipeline import ProcessPipeline
from ...commands.args import DATA
from ...common.date import now, local_time_to_time, format_date, to_date, dates_from, time_to_local_time
from ...common.log import log_current_exception
from ...fit.download.connect import GarminConnect
from ...sql import Constant, SystemConstant

log = getLogger(__name__)

GARMIN_USER = 'garmin_user'
GARMIN_PASSWORD = 'garmin_password'


class GarminReader(ProcessPipeline):

    def __init__(self, *args, force_all=False, **kargs):
        self.__force_all = force_all
        self.__user = None
        self.__password = None
        super().__init__(*args, **kargs)

    def startup(self):
        with self._config.db.session_context(expire_on_commit=False) as s:
            self.__user = Constant.get_single(s, GARMIN_USER, none=True)
            self.__password = Constant.get_single(s, GARMIN_PASSWORD, none=True)
        super().startup()

    def delete(self):
        pass

    def _missing(self, s):
        last = self._config.get_constant(SystemConstant.LAST_GARMIN, none=True)
        if not (self.__user and self.__password):
            log.warning('No username or password defined for Garmin download')
        elif last and (now() - local_time_to_time(last)).total_seconds() < 12 * 60 * 60:
            log.warning(f'Too soon since previous call ({last}; 12 hours minimum)')
        else:
            try:
                dates = [format_date(date) for date in missing_dates(s, force=self.__force_all)]
                if dates:
                    log.debug(f'Download Garmin from {dates[0]}')
                    return dates[:1]  # dates[0] in a list
                else:
                    log.debug('No Garmin data to download')
            except Exception as e:
                log_current_exception()
                log.warning(e)

    def _run_one(self, missed):
        # is only called once with the start date
        data_dir = self._config.args._format_path(DATA)
        connect = GarminConnect(log_response=False)
        connect.login(self.__user, self.__password)

        for repeat, date in enumerate(dates_from(to_date(missed))):
            if repeat:
                sleep(1)
            log.info('Downloading data for %s' % date)
            try:
                connect.get_monitoring_to_fit_file(date, data_dir)
            except HTTPError:
                log_current_exception(traceback=False)
                if self.__force_all:
                    log.warning(f'No data for {date}, but continuing')
                else:
                    log.info('End of data')
                    break

        self._config.set_constant(SystemConstant.LAST_GARMIN, time_to_local_time(now()), True)
        return
