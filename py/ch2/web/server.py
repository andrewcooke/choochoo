from logging import getLogger

from werkzeug import Request, run_simple
from werkzeug.exceptions import HTTPException, BadRequest
from werkzeug.routing import Map, Rule
from werkzeug.serving import WSGIRequestHandler
from werkzeug.wrappers.json import JSONMixin

from .diary import Diary
from .json import JsonResponse
from .jupyter import Jupyter
from .kit import Kit
from .static import Static
from .upload import Upload
from ..commands.args import TUI, LOG, DATABASE, SYSTEM, WEB, SERVICE, VERBOSITY, BIND, PORT, DEV, DATA, UPLOAD
from ..jupyter.server import JupyterController
from ..lib.server import BaseController
from ..sql import SystemConstant


log = getLogger(__name__)


REDIRECT = 'redirect'
ERROR = 'error'
BUSY = 'busy'
REASON = 'reason'
PERCENTAGE = 'percentage'

GET = 'GET'
PUT = 'PUT'
POST = 'POST'


class JSONRequest(Request, JSONMixin):
    pass


class WebController(BaseController):

    def __init__(self, args, sys, db, max_retries=1, retry_secs=1):
        super().__init__(args, sys, WebServer, max_retries=max_retries, retry_secs=retry_secs)
        self.__bind = args[BIND] if BIND in args else None
        self.__port = args[PORT] if BIND in args else None
        self.__dev = args[DEV]
        self.__sys = sys
        self.__db = db
        self.__jupyter = JupyterController(args, sys)

    def _build_cmd_and_log(self, ch2):
        log_name = 'web-service.log'
        cmd = f'{ch2} --{VERBOSITY} {self._log_level} --{TUI} --{LOG} {log_name} --{DATABASE} {self._database} ' \
              f'--{SYSTEM} {self._system} {WEB} {SERVICE} --{BIND} {self.__bind} --{PORT} {self.__port}'
        return cmd, log_name

    def _run(self):
        self._sys.set_constant(SystemConstant.WEB_URL, 'http://%s:%d' % (self.__bind, self.__port), force=True)
        # https://stackoverflow.com/questions/10523879/how-to-make-flask-keep-ajax-http-connection-alive
        WSGIRequestHandler.protocol_version = "HTTP/1.1"
        run_simple(self.__bind, self.__port, WebServer(self.__sys, self.__db, self.__jupyter),
                   use_debugger=self.__dev, use_reloader=self.__dev)

    def _cleanup(self):
        self._sys.delete_constant(SystemConstant.WEB_URL)

    def _status(self, running):
        if running:
            print(f'    {self.connection_url()}')
        print()

    def connection_url(self):
        return self._sys.get_constant(SystemConstant.WEB_URL, none=True)


def error(exception):
    def handler(*args, **kargs):
        raise exception()
    return handler


class WebServer:

    def __init__(self, sys, db, jcontrol):
        self.__sys = sys
        self.__db = db
        diary = Diary()
        kit = Kit()
        static = Static('.static')
        upload = Upload(sys, db)
        jupyter = Jupyter(jcontrol)
        self.url_map = Map([

            Rule('/api/diary/neighbour-activities/<date>', endpoint=diary.read_neighbour_activities, methods=(GET,)),
            Rule('/api/diary/active-days/<month>', endpoint=diary.read_active_days, methods=(GET,)),
            Rule('/api/diary/active-months/<year>', endpoint=diary.read_active_months, methods=(GET,)),
            Rule('/api/diary/analysis-parameters', endpoint=diary.read_analysis_params, methods=(GET,)),
            Rule('/api/diary/statistics', endpoint=diary.write_statistics, methods=(PUT,)),
            Rule('/api/diary/<date>', endpoint=diary.read_diary, methods=(GET,)),

            Rule('/api/kit/edit', endpoint=kit.read_edit, methods=(GET, )),
            Rule('/api/kit/retire-item', endpoint=kit.write_retire_item, methods=(PUT,)),
            Rule('/api/kit/replace-model', endpoint=kit.write_replace_model, methods=(PUT,)),
            Rule('/api/kit/add-component', endpoint=kit.write_add_component, methods=(PUT,)),
            Rule('/api/kit/add-group', endpoint=kit.write_add_group, methods=(PUT,)),
            Rule('/api/kit/items', endpoint=self.check(kit.read_items, ERROR, BUSY), methods=(GET,)),
            Rule('/api/kit/statistics', endpoint=kit.read_statistics, methods=(GET, )),
            Rule('/api/kit/<date>', endpoint=kit.read_snapshot, methods=(GET, )),

            Rule('/api/static/<path:path>', endpoint=static, methods=(GET, )),
            Rule('/api/upload', endpoint=upload, methods=(PUT, )),
            Rule('/api/busy', endpoint=self.read_busy, methods=(GET, )),
            Rule('/api/jupyter/<template>', endpoint=jupyter, methods=(GET, )),
            Rule('/api/<path:path>', endpoint=error(BadRequest), methods=(GET, PUT, POST)),

            Rule('/<path:_>', defaults={'path': 'index.html'}, endpoint=static, methods=(GET,)),
            Rule('/', defaults={'path': 'index.html'}, endpoint=static, methods=(GET,))
        ])

    def dispatch_request(self, request):
        adapter = self.url_map.bind_to_environ(request.environ)
        try:
            endpoint, values = adapter.match()
            values.pop('_', None)
            with self.__db.session_context() as s:
                return endpoint(request, s, **values)
        except HTTPException as e:
            return e

    def wsgi_app(self, environ, start_response):
        request = JSONRequest(environ)
        response = self.dispatch_request(request)
        return response(environ, start_response)

    def __call__(self, environ, start_response):
        return self.wsgi_app(environ, start_response)

    def read_busy(self, request, s):
        percentage = self.__sys.get_percentage(UPLOAD)
        if percentage is None: percentage = 100
        data = {REASON: 'Upload in progress' if percentage < 100 else 'Upload complete',
                PERCENTAGE: percentage}
        return JsonResponse(data)

    def have_error(self):
        return None

    def have_busy(self):
        percentage = self.__sys.get_percentage(UPLOAD)
        if percentage is None or percentage == 100:
            return None
        else:
            return {REDIRECT: '/busy'}

    def check(self, handler, *cases):

        CASE_HANDLERS = {ERROR: self.have_error,
                         BUSY: self.have_busy}

        def wrapper(*args, **kargs):
            for case in cases:
                if case in CASE_HANDLERS:
                    response = CASE_HANDLERS[case]()
                    if response:
                        log.warning(f'Exception for {case}: {response}')
                        return JsonResponse(response)
                else:
                    log.warning(f'Unexpected case for redirect: {case}')
            return JsonResponse({DATA: handler(*args, **kargs)})
        return wrapper
