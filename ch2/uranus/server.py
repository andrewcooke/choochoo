
import asyncio
from threading import Thread

from notebook.notebookapp import NotebookApp
from tornado.platform.asyncio import AnyThreadEventLoopPolicy


def start():
    asyncio.set_event_loop_policy(AnyThreadEventLoopPolicy())
    Thread(target=lambda: ThreadedApp.launch_instance(["--notebook-dir", "/home/andrew/project/ch2/choochoo/notebooks"])).start()


def stop():
    NotebookApp.instance().stop()


class ThreadedApp(NotebookApp):

    def init_signal(self):
        pass
