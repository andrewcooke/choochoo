
from bokeh.server.server import Server


def show(log, plot):

    def callback(doc):
        doc.add_root(plot)

    server = Server({'/': callback})
    server.start()
    log.info('Opening Bokeh application on http://localhost:5006/')
    server.io_loop.add_callback(server.show, "/")
    server.io_loop.call_later(5, server.io_loop.stop)
    server.io_loop.start()
