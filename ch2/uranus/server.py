
import asyncio
from os import makedirs
from os.path import join, exists, isdir
from threading import Thread, Event

from notebook.notebookapp import NotebookApp
from tornado.platform.asyncio import AnyThreadEventLoopPolicy

from ..command.args import JUPYTER, ROOT

JUPYTER_DIR = 'Jupyter.Dir'


def start_from_args(args, log):
    if args[JUPYTER]:
        JupyterServer.singleton(False, 'Jupyter already started')
        notebook_dir = join(args[ROOT], 'notebooks')
        makedirs(notebook_dir, exist_ok=True)

        def start():
            asyncio.set_event_loop_policy(AnyThreadEventLoopPolicy())
            print('isdir? ', isdir(notebook_dir))
            JupyterServer.launch_instance(['--notebook-dir', notebook_dir], log=log)

        t = Thread(target=start)
        t.daemon = True
        t.start()


def stop():
    if JupyterServer.singleton():
        JupyterServer.singleton().stop()


class JupyterServer(NotebookApp):

    def __init__(self, log=None, **kwargs):
        if not log:
            raise Exception('Who is creating this?')
        self._log = log
        super().__init__(**kwargs)

    def init_signal(self):
        self._log.debug('Skipping signal init')

    @classmethod
    def singleton(cls, exists=True, error='No Jupyter server running'):
        if bool(cls._instance) == exists:
            return cls._instance
        else:
            raise Exception(error)
