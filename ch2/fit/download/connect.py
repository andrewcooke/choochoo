
from io import BytesIO
from logging import getLogger
from os.path import join, exists
from re import search, sub
from zipfile import ZipFile

from requests import session

log = getLogger(__name__)


class GarminConnect:

    # logic and data from https://github.com/tcgoetz/GarminDB/blob/master/download_garmin.py
    # and also a bunch more similar scripts

    base_url = 'https://connect.garmin.com'
    sso_url = 'https://sso.garmin.com/sso'
    modern = base_url + '/modern'
    signin = sso_url + '/signin'
    daily = modern + '/proxy/download-service/files/wellness'

    headers = {
        # 'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.13; rv:62.0) Gecko/20100101 Firefox/62.0'
        'User-Agent': 'Mozilla/5.0 (compatible; https://github.com/andrewcooke/choochoo)',
        'origin': 'https://sso.garmin.com'
    }

    def __init__(self, log_response=False):
        self._r = session()
        self._log_response = log_response

    def login(self, username, password):

        log.info('Connecting to Garmin Connect as %s' % username)

        params = {
            # todo - are these all actually needed?  by an sso service?
            'webhost': self.base_url,
            'service': self.modern,
            'source': self.signin,
            'redirectAfterAccountLoginUrl': self.modern,
            'redirectAfterAccountCreationUrl': self.modern,
            'gauthHost': self.sso_url,
            'locale': 'en_US',
            'id': 'gauth-widget',
            'cssUrl': 'https://static.garmincdn.com/com.garmin.connect/ui/css/gauth-custom-v1.2-min.css',
            'clientId': 'GarminConnect',
            'rememberMeShown': 'true',
            'rememberMeChecked': 'false',
            'createAccountShown': 'true',
            'openCreateAccount': 'false',
            'usernameShown': 'false',
            'displayNameShown': 'false',
            'consumeServiceTicket': 'false',
            'initialFocus': 'true',
            'embedWidget': 'false',
            'generateExtraServiceTicket': 'false'
        }

        response = self._log_r(self._r.get(self.signin, headers=self.headers, params=params))
        response.raise_for_status()

        data = {
            'username': username,
            'password': password,
            'embed': 'true',
            'lt': 'e1s1',
            '_eventId': 'submit',
            'displayNameRequired': 'false'
        }

        response = self._log_r(self._r.post(self.signin, headers=self.headers, params=params, data=data))
        response.raise_for_status()

        response_url = search(r'"(https:[^"]+?ticket=[^"]+)"', response.text)
        if not response_url:
            log.debug(response.text)
            raise Exception('Could not find response URL')
        response_url = sub(r'\\', '', response_url.group(1))
        log.debug('Response URL: %s' % response_url)

        response = self._log_r(self._r.get(response_url))
        response.raise_for_status()

    def get_monitoring(self, date):
        response = self._log_r(self._r.get(self.daily + date.strftime('/%Y-%m-%d'), headers=self.headers))
        response.raise_for_status()
        return response

    def _log_r(self, response):
        if self._log_response:
            log.debug('headers: %s' % response.headers)
            log.debug('reason: %s' % response.reason)
            log.debug('cookies: %s' % response.cookies)
            log.debug('history: %s' % response.history)
            # log.debug('text: %s' % response.text)
        return response

    def get_monitoring_to_zip_file(self, date, dir):
        path = join(dir, date.strftime('%Y-%m-%d.zip'))
        if exists(path):
            raise Exception('"%s" already exists' % path)
        response = self.get_monitoring(date)
        with open(path, 'wb') as f:
            f.write(response.content)
        log.info('Downloaded data for %s to %s' % (date, path))

    def get_monitoring_to_fit_file(self, date, dir):
        response = self.get_monitoring(date)
        zipfile = ZipFile(BytesIO(response.content))
        for name in zipfile.namelist():
            path = zipfile.extract(name, path=dir)
            log.info('Downloaded data for %s to %s' % (date, path))
