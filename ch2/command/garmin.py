
from requests import session

from .args import DIR, USER, PASS


BASE_URL = 'https://connect.garmin.com'
SSO_URL = 'https://sso.garmin.com/sso'


def garmin(args, log, db):
    '''
# garmin

    ch2 garmin DIR

    '''
    dir, user, password = args.dir(DIR, rooted=False), args[USER], args[PASS]
    with db.session_context() as s:
        pass
    r = session()
    modern = BASE_URL + '/modern'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.13; rv:62.0) Gecko/20100101 Firefox/62.0'
    }
    params = {
        'webhost': BASE_URL,
        'service': modern,
        'source': SSO_URL + '/signin',
        'redirectAfterAccountLoginUrl': modern,
        'redirectAfterAccountCreationUrl': modern,
        'gauthHost': SSO_URL,
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
    response = r.get(SSO_URL, headers=headers, params=params)
    response.raise_for_status()
    data = {
        'username': user,
        'password': password,
        'embed': 'true',
        'lt': 'e1s1',
        '_eventId': 'submit',
        'displayNameRequired': 'false'
    }

