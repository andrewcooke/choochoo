
from bokeh.application import Application
from bokeh.application.handlers import FunctionHandler
from bokeh.server.server import Server


def show(log, plot, template=None, title=None, template_vars=None):

    template_vars = {} if template_vars is None else template_vars

    def modify_doc(doc):
        doc.add_root(plot)
        doc.title = title
        # this extends bokeh.core.templates.FILE - see code in bokeh.embed.elements
        doc.template = template
        doc.template_variables.update(template_vars)

    app = Application(FunctionHandler(modify_doc))

    server = Server(app)
    server.start()
    log.info('Opening Bokeh application on http://localhost:5006/')
    server.io_loop.add_callback(server.show, "/")
    server.io_loop.call_later(5, server.io_loop.stop)
    server.io_loop.start()
