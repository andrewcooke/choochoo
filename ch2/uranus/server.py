
import asyncio
from os import makedirs
from os.path import join
from threading import Thread, Event
from time import sleep

from notebook.notebookapp import NotebookApp
from tornado.platform.asyncio import AnyThreadEventLoopPolicy

from ..command.args import JUPYTER as J, ROOT


class Jupyter: pass


JUPYTER = Jupyter()
JUPYTER.ENABLED = False
JUPYTER.CONNECTION_URL = None
JUPYTER.NOTEBOOK_DIR = None

__RUNNING = False



def set_jupyter_args(args):
    global JUPYTER
    JUPYTER.ENABLED = args[J]
    JUPYTER.NOTEBOOK_DIR = join(args[ROOT], 'notebooks')
    makedirs(JUPYTER.NOTEBOOK_DIR)


def start_jupyter(log):
    global __RUNNING, JUPYTER
    if JUPYTER.ENABLED and not __RUNNING:
        started = Event()

        def start():
            log.info('Starting Jupyter in separate thread')
            asyncio.set_event_loop_policy(AnyThreadEventLoopPolicy())
            JupyterServer.launch_instance(['--notebook-dir', JUPYTER.NOTEBOOK_DIR], log=log, started=started)

        t = Thread(target=start)
        t.daemon = True
        t.start()
        started.wait()
        sleep(5)  # annoying, but we seem to need extra time or web.open() doesn't work
        __RUNNING = True
        JUPYTER.CONNECTION_URL = JupyterServer._instance.connection_url


def stop_jupyter(log):
    global __RUNNING
    if __RUNNING:
        try:
            JupyterServer._instance.stop()
        except Exception as e:
            log.warning(f'Error stopping Jupyter: {e}')
        __RUNNING = False


class JupyterServer(NotebookApp):

    def __init__(self, log=None, started=None, **kwargs):
        self._log = log
        self._started = started
        super().__init__(**kwargs)

    def init_signal(self):
        self._log.debug('Skipping signal init')

    def start(self):
        self._started.set()
        super().start()
