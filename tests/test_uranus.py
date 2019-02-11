
from logging import basicConfig, getLogger, INFO
from sys import stdout
from tempfile import TemporaryDirectory
from time import sleep
from unittest import TestCase

from ch2.command.args import JUPYTER, ROOT
from ch2.uranus.notebook.notebook import Notebook
from ch2.uranus.server import stop, start_from_args


class TestUranus(TestCase):

    def setUp(self):
        if not getLogger().handlers:
            basicConfig(stream=stdout, level=INFO)
        self._log = getLogger()

    def test_display(self):
        with TemporaryDirectory() as dir:
            print(dir)
            args = {JUPYTER: True, ROOT: dir}
            start_from_args(args, self._log)
            sleep(1)
            notebook = Notebook(self._log, 'foo', 'Hello World')
            notebook.display()
            sleep(3600)
            stop()
