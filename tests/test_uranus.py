
from logging import getLogger, basicConfig, DEBUG
from sys import stdout
from time import sleep
from unittest import TestCase

from ch2.uranus.notebook.support import Notebook
from ch2.uranus.server import start, stop


class TestUranus(TestCase):

    def test_display(self):
        if not getLogger().handlers:
            basicConfig(stream=stdout, level=DEBUG)
        log = getLogger()

        start()
        sleep(1)
        notebook = Notebook(log, 'foo', 'Hello World')
        notebook.display()
        sleep(2)
        stop()
