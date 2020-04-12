
import asyncio
from logging import getLogger
from threading import Thread, Event
from time import sleep

from notebook.notebookapp import NotebookApp
from tornado.platform.asyncio import AnyThreadEventLoopPolicy

from ..commands.args import mm, NOTEBOOKS, JUPYTER, SERVICE, VERBOSITY, TUI, LOG, BASE
from ..lib.server import BaseController
from ..sql import SystemConstant

log = getLogger(__name__)


class JupyterServer(NotebookApp):

    def __init__(self, started, **kwargs):
        self._started = started
        super().__init__(**kwargs)

    @property
    def log_level(self):
        # this silences jupyter's logging
        # the existing mechanism only lets you set a value of 50, which means that "critical" messages
        # are still logged, and the decidedly non-critical usage instructions are printed.
        return 60

    def init_signal(self):
        log.debug('Skipping signal init')

    def start(self):
        self._started.set()
        super().start()


class JupyterController(BaseController):

    def __init__(self, args, sys, max_retries=5, retry_secs=3):
        super().__init__(args, sys, JupyterServer, max_retries=max_retries, retry_secs=retry_secs)
        self.__notebooks = args.system_path(NOTEBOOKS)

    def _status(self, running):
        if running:
            print(f'    {self.connection_url()}')
            print(f'    {self.notebook_dir()}')
        print()

    def _build_cmd_and_log(self, ch2):
        log_name = 'jupyter-service.log'
        cmd = f'{ch2} {mm(VERBOSITY)} {self._log_level} {mm(TUI)} {mm(LOG)} {log_name} {mm(BASE)} {self._base} ' \
              f'{JUPYTER} {SERVICE}'
        return cmd, log_name

    def _cleanup(self):
        self._sys.delete_constant(SystemConstant.JUPYTER_URL)
        self._sys.delete_constant(SystemConstant.JUPYTER_DIR)

    def connection_url(self):
        self.start()
        return self._sys.get_constant(SystemConstant.JUPYTER_URL)

    def notebook_dir(self):
        self.start()
        return self._sys.get_constant(SystemConstant.JUPYTER_DIR)

    def _run(self):

        started = Event()

        def start():
            log.info('Starting Jupyter server in separate thread')
            asyncio.set_event_loop_policy(AnyThreadEventLoopPolicy())
            JupyterServer.launch_instance(['--notebook-dir', self.__notebooks], started=started)

        t = Thread(target=start)
        t.daemon = True
        t.start()
        started.wait()  # set in JupyterServer.start() which is as late as we can get in startup
        log.debug('Separate thread started')

        while not hasattr(JupyterServer._instance, 'connection_url') or not JupyterServer._instance.connection_url:
            log.debug('Waiting for connection URL')
            sleep(1)

        self._sys.set_constant(SystemConstant.JUPYTER_URL, JupyterServer._instance.connection_url, force=True)
        self._sys.set_constant(SystemConstant.JUPYTER_DIR, self.__notebooks, force=True)

        log.info('Jupyter server started')
        while True:
            sleep(1)


__CONTROLLER_SINGLETON = None


def set_controller(controller):
    global __CONTROLLER_SINGLETON
    if __CONTROLLER_SINGLETON:
        raise Exception('Jupyter controller already set')
    __CONTROLLER_SINGLETON = controller
    return __CONTROLLER_SINGLETON


def get_controller():
    if not __CONTROLLER_SINGLETON:
        raise Exception('Jupyter controller not started')
    return __CONTROLLER_SINGLETON
