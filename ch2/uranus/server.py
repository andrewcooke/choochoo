
import asyncio
from logging import getLogger
from os import makedirs, getpid
from os.path import join, expanduser
from threading import Thread, Event
from time import sleep

from notebook.notebookapp import NotebookApp
from tornado.platform.asyncio import AnyThreadEventLoopPolicy

from ..squeal import SystemConstant, SystemProcess
from ..commands.args import ROOT

log = getLogger(__name__)

STARTUP_SLEEP = 3

__RUNNING = False
__ARGS = None
__DIR = None
__URL = None


def set_server_args(args):
    global __ARGS
    __ARGS = args


def start_local():
    global __RUNNING, __URL, __DIR
    if not __RUNNING:
        __DIR, __URL = _start()
        __RUNNING = True


def stop_local():
    _stop()
    __DIR, __URL = None, None


def start_remote(s, command_callback, max_retries=5, sleep_secs=1):
    global __URL, __DIR
    s.commit()  # clear pending writes
    if SystemProcess.exists_any(s, JupyterServer):
        log.debug('Jupyter already running')
    else:
        command_callback()
        retries = 0
        while not SystemProcess.exists_any(s, JupyterServer):
            retries += 1
            if retries > max_retries:
                raise Exception('Jupyter server did not start')
            sleep(sleep_secs)
    __URL = SystemConstant.get(s, SystemConstant.JUPYTER_URL)
    __DIR = SystemConstant.get(s, SystemConstant.JUPYTER_DIR)


def start_service(s):
    dir, url = _start()
    s.add(SystemProcess(pid=getpid(), owner=JupyterServer))
    s.commit()
    SystemConstant.set(s, SystemConstant.JUPYTER_URL, url, force=True)
    SystemConstant.set(s, SystemConstant.JUPYTER_DIR, dir, force=True)


def stop_service(s):
    stop_local()
    SystemProcess.delete_all(s, JupyterServer)
    SystemConstant.delete(s, SystemConstant.JUPYTER_URL)
    SystemConstant.delete(s, SystemConstant.JUPYTER_DIR)


def connection_url():
    if __URL:
        return __URL
    else:
        raise Exception('Jupyter server not started')


def notebook_dir():
    if __DIR:
        return __DIR
    else:
        raise Exception('Jupyter server not started')


def _start():
    global __RUNNING, __ARGS
    dir = expanduser(join(__ARGS[ROOT], 'notebooks'))
    if not __RUNNING:
        log.debug(f'Creating {dir}')
        makedirs(dir, exist_ok=True)

        started = Event()

        def start():
            log.info('Starting Jupyter server in separate thread')
            asyncio.set_event_loop_policy(AnyThreadEventLoopPolicy())
            JupyterServer.launch_instance(['--notebook-dir', dir], started=started)

        t = Thread(target=start)
        t.daemon = True
        t.start()
        started.wait()  # set in JupyterServer.start() which is as late as we can get in startup
        log.debug('Separate thread started')
        sleep(STARTUP_SLEEP)  # annoying, but we seem to need extra time or web.open() doesn't work
        __RUNNING = True

    url = JupyterServer._instance.connection_url
    return dir, url


def _stop():
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

    def __init__(self, started=None, **kwargs):
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
