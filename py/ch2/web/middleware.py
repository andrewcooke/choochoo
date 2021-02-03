from logging import getLogger

from werkzeug import Request
from werkzeug.exceptions import BadRequest

log = getLogger(__name__)


class CsrfCheck:

    # https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html

    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        request = Request(environ)
        if request.method == 'GET':
            log.debug('No CSRF check for GET')
        else:
            if 'CsrfCheck' in request.headers:
                log.debug('Found CsrfCheck')
            else:
                log.error(f'No CsrfCheck header for {request.method}')
                raise BadRequest()
        return self.app(environ, start_response)
