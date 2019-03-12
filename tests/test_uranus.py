
from logging import basicConfig, getLogger, DEBUG
from sys import stdout
from tempfile import TemporaryDirectory
from time import sleep
from unittest import TestCase

from ch2.commands.args import JUPYTER, ROOT
from ch2.uranus.server import set_jupyter_args, stop_jupyter
from ch2.uranus.template.compare_activities import compare_activities


class TestUranus(TestCase):

    def setUp(self):
        if not getLogger().handlers:
            basicConfig(stream=stdout, level=DEBUG)
        self._log = getLogger()

    # def test_template(self):
    #     compare_activities('2018-03-01 16:00', '2017-09-19 16:00', direct=True, group='Bike')

    # def test_display(self):
    #     with TemporaryDirectory() as dir:
    #         try:
    #             self._log.debug(f'Dir {dir}')
    #             set_jupyter_args(self._log, {JUPYTER: True, ROOT: dir})
    #             compare_activities('2018-03-01 16:00', '2017-09-19 16:00', 'Bike', log=self._log)
    #             sleep(5000)
    #         finally:
    #             stop_jupyter(self._log)
