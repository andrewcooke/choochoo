
from ch2.lib.date import parse_datetime, format_datetime


def test_parse_datetime():
    assert format_datetime(parse_datetime('2810-09-21T13:24:01.23')) == '2810-09-21T13:24:01.230000'
    assert format_datetime(parse_datetime('2810-09-21T13:24')) == '2810-09-21T13:24:00.000000'
    assert format_datetime(parse_datetime('2810-09-21')) == '2810-09-21T00:00:00.000000'
