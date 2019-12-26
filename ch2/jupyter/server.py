
import asyncio
from logging import getLogger
from os import makedirs
from threading import Thread, Event
from time import sleep

from notebook.notebookapp import NotebookApp
from tornado.platform.asyncio import AnyThreadEventLoopPolicy

from ..commands.args import NOTEBOOKS, JUPYTER, SERVICE, VERBOSITY, DATABASE, TUI, LOG
from ..lib.workers import command_root
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


class JupyterController:

    def __init__(self, args, system, max_retries=5, retry_secs=3):
        self.__notebooks = args.path(NOTEBOOKS)
        self.__log_level = args[VERBOSITY]
        self.__database = args[DATABASE]
        self.__system = system
        self.__max_retries = max_retries
        self.__retry_secs = retry_secs

    def start_service(self, restart=False):
        if self.__system.exists_any_process(JupyterServer):
            log.debug('Jupyter already running')
            if restart:
                self.stop_service()
            else:
                return
        log.debug('Starting remote Jupyter server')
        ch2 = command_root()
        log_name = 'jupyter-service.log'
        cmd = f'{ch2} --{VERBOSITY} {self.__log_level} --{TUI} --{LOG} {log_name} --{DATABASE} {self.__database} ' \
              f'--{NOTEBOOKS} {self.__notebooks} {JUPYTER} {SERVICE}'
        self.__system.run_process(JupyterServer, cmd, log_name)
        retries = 0
        while not self.__system.exists_any_process(JupyterServer):
            retries += 1
            if retries > self.__max_retries:
                raise Exception('Jupyter server did not start')
            sleep(self.__retry_secs)
        sleep(5)  # extra wait...
        log.info('Jupyter server started')

    def stop_service(self):
        log.info('Stopping any running Jupyter server')
        self.__system.delete_all_processes(JupyterServer)
        self.__system.delete_constant(SystemConstant.JUPYTER_URL)
        self.__system.delete_constant(SystemConstant.JUPYTER_DIR)

    def connection_url(self):
        self.start_service()
        return self.__system.get_constant(SystemConstant.JUPYTER_URL)

    def notebook_dir(self):
        self.start_service()
        return self.__system.get_constant(SystemConstant.JUPYTER_DIR)

    def database_path(self):
        return self.__database

    def run_local(self):
        self.stop_service()

        log.info('Starting a local Jupyter server')
        log.debug(f'Creating {self.__notebooks}')
        makedirs(self.__notebooks, exist_ok=True)

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

        self.__system.set_constant(SystemConstant.JUPYTER_URL, JupyterServer._instance.connection_url, force=True)
        self.__system.set_constant(SystemConstant.JUPYTER_DIR, self.__notebooks, force=True)

        log.info('Jupyter server started')
        while True:
            sleep(1)


__CONTROLLER_SINGLETON = None


def start_controller(args, system):
    global __CONTROLLER_SINGLETON
    if __CONTROLLER_SINGLETON:
        raise Exception('Jupyter controller already started')
    __CONTROLLER_SINGLETON = JupyterController(args, system)


def get_controller():
    if not __CONTROLLER_SINGLETON:
        raise Exception('Jupyter controller not started')
    return __CONTROLLER_SINGLETON


