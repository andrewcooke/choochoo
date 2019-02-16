from unittest import TestCase

from ch2.lib.date import to_time, format_time, local_time_to_time, time_to_local_time


class TestDate(TestCase):

    def test_to_datetime(self):
        self.assertEqual(format_time(to_time('2810-09-21 13:24:01')), '2810-09-21 13:24:01')
        self.assertEqual(format_time(to_time('2810-09-21 13:24')), '2810-09-21 13:24:00')
        self.assertEqual(format_time(to_time('2810-09-21')), '2810-09-21 00:00:00')

    def test_tz(self):
        time = local_time_to_time('2019-02-16 12:19:00')
        self.assertEqual(time, to_time('2019-02-16 15:19:00'))
        self.assertEqual(time_to_local_time(time), '2019-02-16 12:19:00')
