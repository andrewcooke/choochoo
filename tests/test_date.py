
from ch2.lib.date import to_time, format_time


def test_to_datetime():
    assert format_time(to_time('2810-09-21T13:24:01.23')) == '2810-09-21T13:24:01.230000'
    assert format_time(to_time('2810-09-21T13:24')) == '2810-09-21T13:24:00.000000'
    assert format_time(to_time('2810-09-21')) == '2810-09-21T00:00:00.000000'
