
from logging import getLogger

from werkzeug import Request, run_simple
from werkzeug.exceptions import HTTPException, BadRequest
from werkzeug.routing import Map, Rule
from werkzeug.wrappers.json import JSONMixin

from .json import JsonResponse
from .pages.analysis import Analysis
from .pages.configure import Configure
from .pages.diary import Diary
from .pages.jupyter import Jupyter
from .pages.kit import Kit
from .pages.upload import Upload
from .static import Static
from ..commands.args import mm, BASE, TUI, LOG, WEB, SERVICE, VERBOSITY, BIND, PORT, DEV, UPLOAD
from ..jupyter.server import JupyterController
from ..lib.log import log_current_exception
from ..lib.server import BaseController
from ..sql import SystemConstant

log = getLogger(__name__)


DATA = 'data'
REDIRECT = 'redirect'
ERROR = 'error'
BUSY = 'busy'
MESSAGE = 'message'
COMPLETE = 'complete'
PERCENT = 'percent'

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
        self.__base = args.system_path()
        self.__dev = args[DEV]
        self.__sys = sys
        self.__db = db
        self.__jupyter = JupyterController(args, sys)

    def _build_cmd_and_log(self, ch2):
        log_name = 'web-service.log'
        cmd = f'{ch2} {mm(VERBOSITY)} {self._log_level} {mm(TUI)} {mm(LOG)} {log_name} {mm(BASE)} {self._base} ' \
              f'{WEB} {SERVICE} {mm(BIND)} {self.__bind} {mm(PORT)} {self.__port}'
        return cmd, log_name

    def _run(self):
        self._sys.set_constant(SystemConstant.WEB_URL, 'http://%s:%d' % (self.__bind, self.__port), force=True)
        run_simple(self.__bind, self.__port, WebServer(self.__sys, self.__db, self.__jupyter, self.__base),
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
    def handler(*args, **kwargs):
        raise exception()
    return handler


class WebServer:

    def __init__(self, sys, db, jcontrol, base):
        self.__sys = sys
        self.__db = db

        analysis = Analysis()
        configure = Configure(sys, db, base)
        diary = Diary()
        jupyter = Jupyter(jcontrol)
        kit = Kit()
        static = Static('.static')
        upload = Upload(sys, db)

        self.url_map = Map([

            Rule('/api/analysis/parameters', endpoint=self.check(analysis.read_parameters), methods=(GET,)),

            Rule('/api/configure/profiles', endpoint=self.check(configure.read_profiles, config=False), methods=(GET,)),
            Rule('/api/configure/initial', endpoint=self.check(configure.write_profile, config=False), methods=(POST,)),
            Rule('/api/configure/delete', endpoint=self.check(configure.delete, config=False), methods=(POST,)),
            Rule('/api/configure/imported', endpoint=self.check(configure.read_imported), methods=(GET,)),

            Rule('/api/diary/neighbour-activities/<date>', endpoint=diary.read_neighbour_activities, methods=(GET,)),
            Rule('/api/diary/active-days/<month>', endpoint=diary.read_active_days, methods=(GET,)),
            Rule('/api/diary/active-months/<year>', endpoint=diary.read_active_months, methods=(GET,)),
            Rule('/api/diary/statistics', endpoint=self.check(diary.write_statistics), methods=(PUT,)),
            Rule('/api/diary/<date>', endpoint=self.check(diary.read_diary), methods=(GET,)),

            Rule('/api/jupyter/<template>', endpoint=jupyter, methods=(GET, )),

            Rule('/api/kit/edit', endpoint=self.check(kit.read_edit), methods=(GET, )),
            Rule('/api/kit/retire-item', endpoint=self.check(kit.write_retire_item), methods=(PUT,)),
            Rule('/api/kit/replace-model', endpoint=self.check(kit.write_replace_model), methods=(PUT,)),
            Rule('/api/kit/add-component', endpoint=self.check(kit.write_add_component), methods=(PUT,)),
            Rule('/api/kit/add-group', endpoint=self.check(kit.write_add_group), methods=(PUT,)),
            # used by upload
            Rule('/api/kit/items', endpoint=self.check(kit.read_items), methods=(GET,)),
            Rule('/api/kit/statistics', endpoint=self.check(kit.read_statistics), methods=(GET, )),
            Rule('/api/kit/<date>', endpoint=self.check(kit.read_snapshot), methods=(GET, )),

            Rule('/api/static/<path:path>', endpoint=static, methods=(GET, )),

            Rule('/api/upload', endpoint=self.check(upload), methods=(PUT, )),

            Rule('/api/busy', endpoint=self.read_busy, methods=(GET, )),
            Rule('/api/<path:_>', endpoint=error(BadRequest)),

            # ignore path and serve index.html
            Rule('/<path:_>', defaults={'path': 'index.html'}, endpoint=static, methods=(GET,)),
            Rule('/', defaults={'path': 'index.html'}, endpoint=static, methods=(GET,))
        ])

        self.__configure = configure

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

    def get_busy(self):
        percent = self.__sys.get_percent(UPLOAD)
        if percent is None: percent = 100
        # the client uses the complete message when the problem has passed
        return {MESSAGE: 'Loading data and recalculating statistics.',
                COMPLETE: 'Data loaded and statistics updated.',
                PERCENT: percent}

    def read_busy(self, request, s):
        return JsonResponse({BUSY: self.get_busy()})

    def check(self, handler, config=True):

        def wrapper(request, s, *args, **kargs):
            if config and not self.__configure.is_configured():
                log.debug(f'Redirect (not configured)')
                return JsonResponse({REDIRECT: '/configure/initial'})
            busy = self.get_busy()
            if busy[PERCENT] is None or busy[PERCENT] == 100:
                try:
                    data = handler(request, s, *args, **kargs)
                    log.debug(f'Returning data: {data}')
                    return JsonResponse({DATA: data})
                except Exception as e:
                    log_current_exception()
                    # maybe some errors are redirects?
                    error = str(e).strip()
                    if not error.endswith('.'): error += '.'
                    log.debug(f'Returning error: {error}')
                    return JsonResponse({ERROR: error})
            else:
                log.debug(f'Returning busy: {busy}')
                return JsonResponse({BUSY: busy})

        return wrapper
