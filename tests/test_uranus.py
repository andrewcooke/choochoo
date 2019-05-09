
from logging import basicConfig, getLogger, DEBUG
from sys import stdout
from unittest import TestCase


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
