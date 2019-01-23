
from abc import abstractmethod, ABC
from signal import signal, SIGTERM, SIGINT
from threading import Thread

from bokeh.server.server import Server
from tornado.ioloop import IOLoop


SERVER_LOG = None

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


def start(log, app_map):

    global SERVER_LOG

    if SERVER_LOG is None:
        log.info('Starting new server')
        # tornado is weird about ioloops and threads
        # https://github.com/universe-proton/universe-topology/issues/17
        server = Server(app_map, io_loop=IOLoop.instance())
        SERVER_LOG = (server, log)
        server.start()
        Thread(target=server.io_loop.start).start()

        def handler(signal, frame):
            stop()

        signal(SIGTERM, handler)
        signal(SIGINT, handler)

    return SERVER_LOG[0]


def stop():

    global SERVER_LOG

    if SERVER_LOG:
        server, log = SERVER_LOG
        log.debug('Adding shutdown callback')

        def callback():
            log.info('Shutting down server')
            server.io_loop.stop()
            server.stop()
            server.unlisten()
            log.debug('Server shut down')

        server.io_loop.add_callback(callback)


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

    def single_int_param(self, name, values, deflt=__ERROR):
        try:
            return int(values[0])
        except Exception as e:
            msg = 'Could not parse "%s" for %s' % (values, name)
            self._log.warn(msg)
            if deflt != self.__ERROR:
                return deflt
            else:
                raise Exception(msg)

    @abstractmethod
    def create(self, s, **kargs):
        raise NotImplementedError()
