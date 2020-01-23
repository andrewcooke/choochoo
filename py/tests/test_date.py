
import datetime as dt
from unittest import TestCase

from ch2.fit.format.read import filtered_records
from ch2.fit.profile.profile import read_fit
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

    def test_date16(self):
        data = read_fit('data/test/source/other/38014592427.fit')
        # types, messages, records = filtered_records(data, after_records=2342)
        types, messages, records = filtered_records(data)
        previous = None
        for (a, b, record) in records:
            if 'timestamp' in record._fields:
                if previous and previous > record.timestamp:
                    # we have time-travel of 1 minute in this data
                    self.assertTrue(previous - record.timestamp < dt.timedelta(minutes=2),
                                    f'{previous} -> {record.timestamp}')
                previous = record.timestamp
