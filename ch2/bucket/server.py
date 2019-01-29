
from abc import abstractmethod, ABC
from threading import Thread

from bokeh.server.server import Server
from tornado.ioloop import IOLoop

from ..lib.date import to_time, to_date

SINGLETON = None

TEMPLATE = '''
{% block css_resources %}
  {{ super() }}
  <style>
body {
  background-color: white;
}
.centre {
  text-align: center
}
.centre > div {
  display: inline-block;
}
a {
  color: black;
  text-decoration: none;
  border-bottom: 1px dotted black;
}
a:hover {
  border-bottom: 1px solid black;
}
table {
  margin: 20px;
  border-spacing: 10px;
}
  </style>
{% endblock %}
{% block inner_body %}
  <div class='centre'>
  <h1>{{ header }}</h1>
  {{ super() }}
  </div>
{% endblock %}
'''


class ServerThread(Server):

    def __init__(self, log, app_map):
        self._log = log
        super().__init__(app_map, io_loop=IOLoop.instance())
        Thread(target=self.io_loop.start).start()

    def stop(self):

        def callback():
            self._log.info('Shutting down server')
            self.io_loop.stop()
            super(ServerThread, self).stop(wait=True)
            self.unlisten()
            self._log.debug('Server shut down')

        self.io_loop.add_callback(callback)


def default_singleton_server(log, db):

    from .page.activity_details import ActivityDetailsPage
    from .page.duration_activities import DurationActivitiesPage
    from .page.similar_activities import SimilarActivitiesPage

    return singleton_server(log, {SimilarActivitiesPage.PATH: SimilarActivitiesPage(log, db),
                                  ActivityDetailsPage.PATH: ActivityDetailsPage(log, db),
                                  DurationActivitiesPage.PATH: DurationActivitiesPage(log, db)})


def singleton_server(log, app_map):

    global SINGLETON

    if SINGLETON is None:
        log.info('Starting new server')
        # tornado is weird about ioloops and threads
        # https://github.com/universe-proton/universe-topology/issues/17
        SINGLETON = ServerThread(log, app_map)

    return SINGLETON


class Page(ABC):

    def __init__(self, log, db, template=TEMPLATE, **vars):
        self._log = log
        self._db = db
        self._template = template
        self._vars = vars

    def __call__(self, doc):
        self._log.debug('Page called with %s' % doc)
        with self._db.session_context() as s:
            params = doc.session_context.request.arguments
            self._log.debug('Request params: %s' % params)
            vars, root = self.create(s, **params)
            vars = vars if vars is not None else {}
            vars.update(self._vars)
            doc.add_root(root)
            doc.template = self._template
            doc.template_variables.update(vars)
            doc.title = vars['title'] if 'title' in vars else 'Choochoo'

    __ERROR = object()

    def _parse_error(self, name, values, deflt):
        msg = 'Could not parse "%s" for %s' % (values, name)
        self._log.warning(msg)
        if deflt != self.__ERROR:
            return deflt
        else:
            raise Exception(msg)

    def _single_param(self, type, name, values, deflt=__ERROR):
        try:
            return type(values[0].decode())
        except Exception as e:
            self._log.warn(e)
            return self._parse_error(name, values, deflt)

    def single_int_param(self, name, values, deflt=__ERROR):
        return self._single_param(int, name, values, deflt)

    def single_time_param(self, name, values, deflt=__ERROR):
        return self._single_param(to_time, name, values, deflt)

    def single_date_param(self, name, values, deflt=__ERROR):
        return self._single_param(to_date, name, values, deflt)

    @abstractmethod
    def create(self, s, **kargs):
        raise NotImplementedError()
