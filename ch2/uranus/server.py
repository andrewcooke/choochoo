
import asyncio
from _signal import pause
from logging import getLogger
from os import makedirs
from threading import Thread, Event
from time import sleep

from notebook.notebookapp import NotebookApp
from tornado.platform.asyncio import AnyThreadEventLoopPolicy

from ..commands.args import NOTEBOOKS, JUPYTER, SERVICE
from ..lib.workers import command_root
from ..squeal import SystemConstant, SystemProcess

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


class JupyterController:

    def __init__(self, db, args, max_retries=5, retry_secs=3):
        self._db = db
        self._notebooks = args.path(NOTEBOOKS)
        self._max_retries = max_retries
        self._retry_secs = retry_secs

    def start_service(self):
        with self._db.session_context() as s:
            if SystemProcess.exists_any(s, JupyterServer):
                log.debug('Jupyter already running')
            else:
                log.debug('Starting remote Jupyter server')
                ch2 = command_root()
                log_name = 'jupyter-service.log'
                cmd = f'{ch2} -v0 -l {log_name} --{NOTEBOOKS} {self._notebooks} {JUPYTER} {SERVICE}'
                SystemProcess.run(s, cmd, log_name, JupyterServer)
                retries = 0
                while not SystemProcess.exists_any(s, JupyterServer):
                    retries += 1
                    if retries > self._max_retries:
                        raise Exception('Jupyter server did not start')
                    sleep(self._retry_secs)
                log.debug('Jupyter server started')

    def stop_service(self):
        log.info('Stopping any running Jupyter server')
        with self._db.session_context() as s:
            SystemProcess.delete_all(s, JupyterServer)
            SystemConstant.delete(s, SystemConstant.JUPYTER_URL)
            SystemConstant.delete(s, SystemConstant.JUPYTER_DIR)

    def connection_url(self):
        self.start_service()
        with self._db.session_context() as s:
            return SystemConstant.get(s, SystemConstant.JUPYTER_URL)

    def notebook_dir(self):
        self.start_service()
        with self._db.session_context() as s:
            return SystemConstant.get(s, SystemConstant.JUPYTER_DIR)

    def run_local(self):
        self.stop_service()

        log.info('Starting a local Jupyter server')
        log.debug(f'Creating {self._notebooks}')
        makedirs(self._notebooks, exist_ok=True)

        started = Event()

        def start():
            log.info('Starting Jupyter server in separate thread')
            asyncio.set_event_loop_policy(AnyThreadEventLoopPolicy())
            JupyterServer.launch_instance(['--notebook-dir', self._notebooks], started=started)

        t = Thread(target=start)
        t.daemon = True
        t.start()
        started.wait()  # set in JupyterServer.start() which is as late as we can get in startup
        log.debug('Separate thread started')

        while not hasattr(JupyterServer._instance, 'connection_url') or not JupyterServer._instance.connection_url:
            log.debug('Waiting for connection URL')
            sleep(1)

        with self._db.session_context() as s:
            SystemConstant.set(s, SystemConstant.JUPYTER_URL, JupyterServer._instance.connection_url, force=True)
            SystemConstant.set(s, SystemConstant.JUPYTER_DIR, self._notebooks, force=True)

        log.info('Jupyter server started')
        pause()


__CONTROLLER_SINGLETON = None


def start_controller(db, args):
    global __CONTROLLER_SINGLETON
    if __CONTROLLER_SINGLETON:
        raise Exception('Jupyter controller already started')
    __CONTROLLER_SINGLETON = JupyterController(db, args)


def get_controller():
    if not __CONTROLLER_SINGLETON:
        raise Exception('Jupyter controller not started')
    return __CONTROLLER_SINGLETON
