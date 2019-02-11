
import asyncio
from os import makedirs
from os.path import join, exists, isdir
from threading import Thread

from notebook.notebookapp import NotebookApp
from tornado.platform.asyncio import AnyThreadEventLoopPolicy

from ..command.args import JUPYTER, ROOT

JUPYTER_DIR = 'Jupyter.Dir'
SINGLETON = None


def start_from_args(args, log):

    global SINGLETON

    if args[JUPYTER]:
        if SINGLETON:
            raise Exception('Jupyter already started')
        notebook_dir = join(args[ROOT], 'notebooks')
        makedirs(notebook_dir, exist_ok=True)
        print(notebook_dir)

        def start():
            asyncio.set_event_loop_policy(AnyThreadEventLoopPolicy())
            print('isdir? ', isdir(notebook_dir))
            JupyterServer.launch_instance(['--notebook-dir', notebook_dir], log=log)

        t = Thread(target=start)
        t.daemon = True
        t.start()
        SINGLETON = JupyterServer.instance()


def jupyter_server():
    if SINGLETON:
        return SINGLETON
    else:
        raise Exception('Jupyter not running')


def stop():
    global SINGLETON
    if SINGLETON:
        SINGLETON.stop()
        SINGLETON = None


class JupyterServer(NotebookApp):

    def __init__(self, log=None, **kwargs):
        self._log = log
        super().__init__(**kwargs)

    def init_signal(self):
        self._log.debug('Skipping signal init')
