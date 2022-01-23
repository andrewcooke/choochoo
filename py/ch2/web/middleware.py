from logging import getLogger

from werkzeug import Request
from werkzeug.datastructures import Headers
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


class CORS:

    # https://github.com/pallets/werkzeug/issues/131#issuecomment-35599744

    def __init__(self, app, origin):
        self.app = app
        self.origin = origin

    def __call__(self, environ, start_response):

        def add_cors_headers(status, headers, exc_info=None):
            headers = Headers(headers)
            headers.add("Access-Control-Allow-Origin", self.origin)
            headers.add("Access-Control-Allow-Headers", "CsrfCheck, content-type")
            headers.add("Access-Control-Allow-Credentials", "true")
            headers.add("Access-Control-Allow-Methods", "GET, POST, PUT")
            headers.add("Access-Control-Expose-Headers", "...")
            return start_response(status, headers, exc_info)

        if environ.get("REQUEST_METHOD") == "OPTIONS":
            add_cors_headers("200 Ok", [("Content-Type", "text/plain")])
            return [b'200 Ok']

        return self.app(environ, add_cors_headers)
