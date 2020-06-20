
import asyncio
from logging import getLogger
from os import geteuid
from threading import Thread, Event
from time import sleep

from notebook.notebookapp import NotebookApp
from tornado.platform.asyncio import AnyThreadEventLoopPolicy
from uritools import urisplit, uriunsplit

from ..commands.args import mm, NOTEBOOKS, JUPYTER, SERVICE, VERBOSITY, LOG, BASE, base_system_path, BIND, PORT, PROXY
from ..global_ import global_dev
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

    def __init__(self, args, data, max_retries=5, retry_secs=3):
        super().__init__(JUPYTER, args, data, JupyterServer, max_retries=max_retries, retry_secs=retry_secs)
        self._proxy_bind = self.__proxy_args(args, BIND, self._bind)
        self._proxy_port = self.__proxy_args(args, PORT, self._port)

    @staticmethod
    def __proxy_args(args, name, default):
        full_name = PROXY + '-' + name
        if full_name in args and args[full_name]:
            return args[full_name]
        else:
            return default

    def _status(self, running):
        if running:
            print(f'    {self.connection_url()}')
        print()

    def _build_cmd_and_log(self, ch2):
        log_name = 'jupyter-service.log'
        cmd = f'{ch2} {mm(VERBOSITY)} 5 {mm(LOG)} {log_name} {mm(BASE)} {self._data.base} ' \
              f'{JUPYTER} {SERVICE} {mm(JUPYTER + "-" + BIND)} {self._bind} {mm(JUPYTER + "-" + PORT)} {self._port}'
        if self._proxy_bind: cmd += f' {mm(PROXY + "-" + BIND)} {self._proxy_bind}'
        if self._proxy_port: cmd += f' {mm(PROXY + "-" + PORT)} {self._proxy_port}'
        return cmd, log_name

    def _cleanup(self):
        self._data.sys.delete_constant(SystemConstant.JUPYTER_URL)

    def connection_url(self):
        self.start()
        return self._data.sys.get_constant(SystemConstant.JUPYTER_URL)

    def base_dir(self):
        return self._data.base

    def _run(self):

        started = Event()

        def start():
            log.info('Starting Jupyter server in separate thread')
            asyncio.set_event_loop_policy(AnyThreadEventLoopPolicy())
            notebook_dir = base_system_path(self._data.base, subdir=NOTEBOOKS)
            options = ['--notebook-dir', notebook_dir]
            if self._bind is not None: options += ['--ip', self._bind]
            if self._port is not None: options += ['--port', str(self._port)]
            if global_dev(): options += ['--debug', '--log-level=DEBUG']
            if not geteuid(): options += ['--allow-root', '--no-browser']
            # https://github.com/jupyter/notebook/issues/2254
            options += ['--NotebookApp.token=""']
            log.debug(f'Jupyter options: {options}')
            JupyterServer.launch_instance(options, started=started)

        t = Thread(target=start)
        t.daemon = True
        t.start()
        started.wait()  # set in JupyterServer.start() which is as late as we can get in startup
        log.debug('Separate thread started')

        while not hasattr(JupyterServer._instance, 'connection_url') or not JupyterServer._instance.connection_url:
            log.debug('Waiting for connection URL')
            sleep(1)
        old_url = JupyterServer._instance.connection_url
        new_url = uriunsplit(urisplit(old_url)._replace(authority=f'{self._proxy_bind}:{self._proxy_port}'))
        log.debug(f'Rewrote {old_url} -> {new_url}')
        self._data.sys.set_constant(SystemConstant.JUPYTER_URL, new_url, force=True)

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
