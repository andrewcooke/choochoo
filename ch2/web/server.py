
from logging import getLogger

from werkzeug import Response, Request, run_simple

from ..commands.args import TUI, LOG, DATABASE, SYSTEM, WEB, SERVICE, VERBOSITY, BIND, PORT, DEV
from ..lib.server import BaseController

log = getLogger(__name__)


class WebController(BaseController):

    def __init__(self, args, sys, max_retries=1, retry_secs=1):
        super().__init__(args, sys, Web, max_retries=max_retries, retry_secs=retry_secs)
        self.__bind = args[BIND] if BIND in args else None
        self.__port = args[PORT] if BIND in args else None
        self.__dev = args[DEV]

    def _build_cmd_and_log(self, ch2):
        log_name = 'web-service.log'
        cmd = f'{ch2} --{VERBOSITY} {self._log_level} --{TUI} --{LOG} {log_name} --{DATABASE} {self._database} ' \
              f'--{SYSTEM} {self._system} {WEB} {SERVICE} --{BIND} {self.__bind} --{PORT} {self.__port}'
        return cmd, log_name

    def _run(self):
        run_simple(self.__bind, self.__port, make_app(), use_debugger=self.__dev)


def make_app():
    return Web()


class Web(object):

    def __init__(self):
        pass

    def dispatch_request(self, request):
        return Response('Hello World!')

    def wsgi_app(self, environ, start_response):
        request = Request(environ)
        response = self.dispatch_request(request)
        return response(environ, start_response)

    def __call__(self, environ, start_response):
        return self.wsgi_app(environ, start_response)

