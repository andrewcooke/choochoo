
import asyncio
from os import makedirs
from os.path import join, expanduser
from threading import Thread, Event
from time import sleep

from notebook.notebookapp import NotebookApp
from tornado.platform.asyncio import AnyThreadEventLoopPolicy

from ..commands.args import JUPYTER as J, ROOT


class JupyterState: pass


JUPYTER = JupyterState()
JUPYTER.ENABLED = False
JUPYTER.CONNECTION_URL = None
JUPYTER.NOTEBOOK_DIR = None

__RUNNING = False


def set_jupyter_args(log, args):
    global JUPYTER
    JUPYTER.ENABLED = args[J]
    JUPYTER.NOTEBOOK_DIR = expanduser(join(args[ROOT], 'notebooks'))
    log.debug(f'Creating {JUPYTER.NOTEBOOK_DIR}')
    makedirs(JUPYTER.NOTEBOOK_DIR, exist_ok=True)


def start_jupyter(log):
    global __RUNNING, JUPYTER
    if JUPYTER.ENABLED and not __RUNNING:
        started = Event()

        def start():
            log.info('Starting Jupyter server in separate thread')
            asyncio.set_event_loop_policy(AnyThreadEventLoopPolicy())
            JupyterServer.launch_instance(['--notebook-dir', JUPYTER.NOTEBOOK_DIR], log=log, started=started)

        t = Thread(target=start)
        t.daemon = True
        t.start()
        started.wait()  # set in JupyterServer.start() which is as late as we can get in startup
        sleep(5)  # annoying, but we seem to need extra time or web.open() doesn't work
        __RUNNING = True
        JUPYTER.CONNECTION_URL = JupyterServer._instance.connection_url


def stop_jupyter(log):
    global __RUNNING
    if __RUNNING:
        try:
            log.info('Stopping Jupyter server')
            JupyterServer._instance.stop()
            log.debug('Jupyter server stopped')
        except Exception as e:
            log.warning(f'Error stopping Jupyter: {e}')
        finally:
            __RUNNING = False
    else:
        log.debug('Jupyter server not running')


class JupyterServer(NotebookApp):

    def __init__(self, log=None, started=None, **kwargs):
        self._log = log
        self._started = started
        super().__init__(**kwargs)

    @property
    def log_level(self):
        # this silences jupyter's logging
        # the existing mechanism only lets you set a value of 50, which means that "critical" messages
        # are still logged, and the decidedly non-critical usage instructions are printed.
        return 60

    def init_signal(self):
        self._log.debug('Skipping signal init')

    def start(self):
        self._started.set()
        super().start()
