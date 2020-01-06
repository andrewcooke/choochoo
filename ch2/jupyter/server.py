
import asyncio
from logging import getLogger
from os import makedirs
from threading import Thread, Event
from time import sleep

from notebook.notebookapp import NotebookApp
from tornado.platform.asyncio import AnyThreadEventLoopPolicy

from ..commands.args import NOTEBOOKS, JUPYTER, SERVICE, VERBOSITY, DATABASE, TUI, LOG, SYSTEM
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

    def __init__(self, args, sys, max_retries=5, retry_secs=3):
        self.__notebooks = args.path(NOTEBOOKS)
        self.__log_level = args[VERBOSITY]
        self.__database = args[DATABASE]
        self.__system = args[SYSTEM]
        self.__sys = sys
        self.__max_retries = max_retries
        self.__retry_secs = retry_secs

    def status(self):
        if self.__sys.exists_any_process(JupyterServer):
            print('\n  Service running:')
            print(f'    {self.connection_url()}')
            print(f'    {self.notebook_dir()}\n')
        else:
            print('\n  No service running\n')

    def start_service(self, restart=False):
        if self.__sys.exists_any_process(JupyterServer):
            log.debug('Jupyter already running')
            if restart:
                self.stop_service()
            else:
                return
        log.debug('Starting remote Jupyter server')
        ch2 = command_root()
        log_name = 'jupyter-service.log'
        cmd = f'{ch2} --{VERBOSITY} {self.__log_level} --{TUI} --{LOG} {log_name} --{DATABASE} {self.__database} ' \
              f'--{SYSTEM} {self.__system} --{NOTEBOOKS} {self.__notebooks} {JUPYTER} {SERVICE}'
        self.__sys.run_process(JupyterServer, cmd, log_name)
        retries = 0
        while not self.__sys.exists_any_process(JupyterServer):
            retries += 1
            if retries > self.__max_retries:
                raise Exception('Jupyter server did not start')
            sleep(self.__retry_secs)
        sleep(5)  # extra wait...
        log.info('Jupyter server started')

    def stop_service(self):
        log.info('Stopping any running Jupyter server')
        self.__sys.delete_all_processes(JupyterServer)
        self.__sys.delete_constant(SystemConstant.JUPYTER_URL)
        self.__sys.delete_constant(SystemConstant.JUPYTER_DIR)

    def connection_url(self):
        self.start_service()
        return self.__sys.get_constant(SystemConstant.JUPYTER_URL)

    def notebook_dir(self):
        self.start_service()
        return self.__sys.get_constant(SystemConstant.JUPYTER_DIR)

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

        self.__sys.set_constant(SystemConstant.JUPYTER_URL, JupyterServer._instance.connection_url, force=True)
        self.__sys.set_constant(SystemConstant.JUPYTER_DIR, self.__notebooks, force=True)

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
