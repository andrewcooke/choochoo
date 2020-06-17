
from logging import getLogger

from werkzeug import Request, run_simple
from werkzeug.exceptions import HTTPException, BadRequest
from werkzeug.routing import Map, Rule
from werkzeug.wrappers.json import JSONMixin

from .json import JsonResponse
from .servlets.analysis import Analysis
from .servlets.thumbnail import Thumbnail
from .servlets.configure import Configure
from .servlets.diary import Diary
from .servlets.jupyter import Jupyter
from .servlets.kit import Kit
from .servlets.search import Search
from .servlets.upload import Upload
from .static import Static
from ..commands.args import mm, BASE, LOG, WEB, SERVICE, VERBOSITY, BIND, PORT, DEV, READ, URI, JUPYTER, WARN, SECURE
from ..jupyter.server import JupyterController
from ..lib.log import log_current_exception
from ..lib.server import BaseController
from ..sql import SystemConstant

log = getLogger(__name__)


MAX_MSG = 1000

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

    def __init__(self, args, data, max_retries=1, retry_secs=1):
        super().__init__(WEB, args, data, WebServer, max_retries=max_retries, retry_secs=retry_secs)
        self.__uri = args[URI]
        self.__warn_data = args[WARN + '-' + DATA]
        self.__warn_secure = args[WARN + '-' + SECURE]
        self.__jupyter = JupyterController(args, data)

    def _build_cmd_and_log(self, ch2):
        log_name = 'web-service.log'
        cmd = f'{ch2} {mm(VERBOSITY)} 0 {mm(LOG)} {log_name} {mm(BASE)} {self._data.base} ' \
              f'{WEB} {SERVICE} {mm(WEB + "-" + BIND)} {self._bind} {mm(WEB + "-" + PORT)} {self._port}' \
              f'{mm(JUPYTER + "-" + BIND)} {self.__jupyter._bind} {mm(JUPYTER + "-" + PORT)} {self.__jupyter._port}'
        if self.__warn_data: cmd += f' {mm(WARN + "-" + DATA)}'
        if self.__warn_secure: cmd += f' {mm(WARN + "-" + SECURE)}'
        return cmd, log_name

    def _run(self):
        self._data.sys.set_constant(SystemConstant.WEB_URL, 'http://%s:%d' % (self._bind, self._port), force=True)
        log.debug(f'Binding to {self._bind}:{self._port} with Jupyter at {self.__jupyter} and URI {self.__uri}')
        run_simple(self._bind, self._port,
                   WebServer(self._data, self.__jupyter, self.__uri,
                             warn_data=self.__warn_data, warn_secure=self.__warn_secure),
                   use_debugger=self._dev, use_reloader=self._dev)

    def _cleanup(self):
        self._data.sys.delete_constant(SystemConstant.WEB_URL)

    def _status(self, running):
        if running:
            print(f'    {self.connection_url()}')
        print()

    def connection_url(self):
        return self._data.sys.get_constant(SystemConstant.WEB_URL, none=True)


def error(exception):
    def handler(*args, **kwargs):
        raise exception()
    return handler


class WebServer:

    def __init__(self, data, jcontrol, uri, warn_data=False, warn_secure=False):
        self.__data = data
        self.__warn_data = warn_data
        self.__warn_secure = warn_secure

        analysis = Analysis()
        configure = Configure(data, uri)
        diary = Diary()
        jupyter = Jupyter(jcontrol)
        kit = Kit()
        static = Static('.static')
        upload = Upload(data)
        thumbnail = Thumbnail(data.base)
        search = Search()

        self.url_map = Map([

            Rule('/api/analysis/parameters', endpoint=self.check(analysis.read_parameters), methods=(GET,)),

            Rule('/api/configure/profiles', endpoint=self.check(configure.read_profiles, config=False), methods=(GET,)),
            Rule('/api/configure/initial', endpoint=self.check(configure.write_profile, config=False), methods=(POST,)),
            Rule('/api/configure/delete', endpoint=self.check(configure.delete, config=False), methods=(POST,)),
            Rule('/api/configure/import', endpoint=self.check(configure.read_import), methods=(GET,)),
            Rule('/api/configure/import', endpoint=self.check(configure.write_import), methods=(POST,)),
            Rule('/api/configure/constants', endpoint=self.check(configure.read_constants), methods=(GET,)),
            Rule('/api/configure/constant', endpoint=self.check(configure.write_constant), methods=(PUT,)),

            Rule('/api/diary/neighbour-activities/<date>', endpoint=diary.read_neighbour_activities, methods=(GET,)),
            Rule('/api/diary/active-days/<month>', endpoint=diary.read_active_days, methods=(GET,)),
            Rule('/api/diary/active-months/<year>', endpoint=diary.read_active_months, methods=(GET,)),
            Rule('/api/diary/statistics', endpoint=self.check(diary.write_statistics), methods=(PUT,)),
            Rule('/api/diary/latest', endpoint=diary.read_latest, methods=(GET,)),
            Rule('/api/diary/<date>', endpoint=self.check(diary.read_diary), methods=(GET,)),

            Rule('/api/search/activity/<query>', endpoint=search.query_activity, methods=(GET,)),
            Rule('/api/search/activity-terms', endpoint=search.read_activity_terms, methods=(GET,)),

            Rule('/api/jupyter/<template>', endpoint=jupyter, methods=(GET, )),

            Rule('/api/kit/edit', endpoint=self.check(kit.read_edit), methods=(GET, )),
            Rule('/api/kit/retire-item', endpoint=self.check(kit.write_retire_item), methods=(PUT,)),
            Rule('/api/kit/replace-model', endpoint=self.check(kit.write_replace_model), methods=(PUT,)),
            Rule('/api/kit/add-component', endpoint=self.check(kit.write_add_component), methods=(PUT,)),
            Rule('/api/kit/add-group', endpoint=self.check(kit.write_add_group), methods=(PUT,)),
            Rule('/api/kit/items', endpoint=self.check(kit.read_items), methods=(GET,)),
            Rule('/api/kit/statistics', endpoint=self.check(kit.read_statistics), methods=(GET, )),
            Rule('/api/kit/<date>', endpoint=self.check(kit.read_snapshot), methods=(GET, )),

            Rule('/api/thumbnail/<activity>', endpoint=thumbnail, methods=(GET, )),
            Rule('/api/static/<path:path>', endpoint=static, methods=(GET, )),

            Rule('/api/upload', endpoint=self.check(upload), methods=(PUT, )),

            Rule('/api/busy', endpoint=self.read_busy, methods=(GET, )),
            Rule('/api/warnings', endpoint=self.read_warnings, methods=(GET, )),
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
            if self.__data.db:
                with self.__data.db.session_context() as s:
                    return endpoint(request, s, **values)
            else:
                return endpoint(request, None, **values)
        except HTTPException as e:
            return e

    def wsgi_app(self, environ, start_response):
        request = JSONRequest(environ)
        response = self.dispatch_request(request)
        return response(environ, start_response)

    def __call__(self, environ, start_response):
        return self.wsgi_app(environ, start_response)

    def get_busy(self):
        percent = self.__data.sys.get_percent(READ)
        if percent is None: percent = 100
        # the client uses the complete message when the problem has passed
        return {MESSAGE: 'Loading data and recalculating statistics.',
                COMPLETE: 'Data loaded and statistics updated.',
                PERCENT: percent}

    def read_busy(self, request, s):
        return JsonResponse({BUSY: self.get_busy()})

    def read_warnings(self, request, s):
        warnings = []
        if self.__warn_data:
            warnings.append({'title': 'Your Data Are Not Stored Permanently',
                             'text': 'The default Docker configuration stores your data within the same '
                                     'container that runs the code.  If you update / delete / prune the '
                                     'container you will lose your data.'})
        if self.__warn_secure:
            warnings.append({'title': 'This System Is Not Secured For External Use',
                             'text': 'Choochoo should not be deployed on a public server.  '
                                     'It is intended only for local, personal use.'})
        return JsonResponse({DATA: warnings})

    def check(self, handler, config=True):

        def wrapper(request, s, *args, **kargs):
            if config and not self.__configure.is_configured():
                log.debug(f'Redirect (not configured)')
                return JsonResponse({REDIRECT: '/configure/initial'})
            busy = self.get_busy()
            if busy[PERCENT] is None or busy[PERCENT] == 100:
                try:
                    data = handler(request, s, *args, **kargs)
                    msg = f'Returning data: {data}'
                    if len(msg) > MAX_MSG:
                        msg = msg[:MAX_MSG-20] + ' ... ' + msg[-10:]
                    log.debug(msg)
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
