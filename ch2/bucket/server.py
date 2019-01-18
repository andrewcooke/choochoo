
from bokeh.server.server import Server


class SingleShotServer:

    def __init__(self, log, plot, template=None, title=None, template_vars=None, pause=60):
        self.__log = log
        self.__plot = plot
        self.__template = template
        self.__title = title
        self.__template_vars = {} if template_vars is None else template_vars
        self.__server = Server(self.__modify_doc)

        self.__server.start()
        self.__log.info('Opening Bokeh application on http://localhost:5006/')
        self.__server.io_loop.add_callback(self.__server.show, "/")
        self.__server.io_loop.call_later(pause, self.__stop)
        self.__server.io_loop.start()

    def __modify_doc(self, doc):
        doc.add_root(self.__plot)
        doc.title = self.__title
        # this extends bokeh.core.templates.FILE - see code in bokeh.embed.elements
        doc.template = self.__template
        doc.template_variables.update(self.__template_vars)

    def __stop(self):
        self.__log.info('Stopping server')
        self.__server.io_loop.stop()
        self.__server.stop()
        self.__server.unlisten()
