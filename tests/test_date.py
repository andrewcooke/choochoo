
from ch2.lib.date import to_time, format_time


def test_to_datetime():
    assert format_time(to_time('2810-09-21 13:24:01')) == '2810-09-21 13:24:01'
    assert format_time(to_time('2810-09-21 13:24')) == '2810-09-21 13:24:00'
    assert format_time(to_time('2810-09-21')) == '2810-09-21 00:00:00'
