
import datetime as dt

from choochoo.lib.repeating import Specification, DateOrdinals


def assert_str(x, s):
    assert str(x) == s, '%s != %s' % (str(x), s)


def assert_bad(f, *args):
    ok = True
    try:
        f(*args)
    except:
        ok = False
    assert not ok, '%s %s' % (f, args)


def test_specification():
    # from the spec doc
    assert_str(Specification('m[2Tue]'), '0/1m[2tue]')
    assert_str(Specification('2m[2Tue]'), '0/2m[2tue]')
    assert_str(Specification('1/2m[2Tue]'), '1/2m[2tue]')
    assert_str(Specification('m[2Tue]1970-01-01-1970-12-31'), '0/1m[2tue]1970-01-01-1970-12-31')
    assert_str(Specification('2018-07-05/5d[]'), '2/5d[1]')
    assert_str(Specification('d2018-07-05'), '0/1d[1]2018-07-05')
    # others
    assert_str(Specification('1/2w[1]2018-01-01-'), '1/2w[1]2018-01-01-')
    assert_str(Specification('1/2w[Mon,2,3]-1970-01-01'), '1/2w[1mon,2,3]-1970-01-01')
    # some errors
    assert_bad(Specification, '1/2[]2018-01-01-')   # must specify type
    assert_bad(Specification, '1/2w[1d]2018-01-01-')  # no longer support type in location


def assert_at(spec, date, at_frame, at_location):
    ordinals = DateOrdinals(date)
    frame = Specification(spec).frame()
    assert frame.at_frame(ordinals) == at_frame, '%s %s' % (spec, date)
    assert frame.at_location(ordinals) == at_location, '%s %s' % (spec, date)


def test_day():
    assert_at('d', '2018-07-06', True, True)
    assert_at('d', '2018-07-07', True, True)
    assert_at('2d', '2018-07-06', True, True)
    assert_at('2d', '2018-07-07', False, False)
    assert_at('2d[1]', '2018-07-06', True, True)
    assert_at('2d[2]', '2018-07-06', True, False)
    assert_at('2d[Fri]', '2018-07-06', True, True)
    assert_at('2d[1Fri]', '2018-07-06', True, True)
    assert_at('2d[2Fri]', '2018-07-06', True, False)
    assert_at('2d[Mon]', '2018-07-06', True, False)
    assert_at('2d[Fri]2018-07-06', '2018-07-06', True, True)
    assert_at('2d[Fri]2018-07-07', '2018-07-06', False, False)
    assert_at('2d[Fri]2018-07-06-2018-07-06', '2018-07-06', True, True)
    assert_at('2d[Fri]2018-07-07-2018-07-07', '2018-07-06', False, False)
    assert_at('2d[Fri]2018-07-05-2018-07-05', '2018-07-06', False, False)


def test_week():
    assert_at('2018-07-06/w[Fri]', '2018-07-06', True, True)
    assert_at('2018-07-06/w[Fri]', '2018-07-05', True, False)
    assert_at('2018-07-06/w[Fri]', '2018-07-07', True, False)
    assert_at('2018-07-06/w[1]', '2018-07-02', True, True)
    assert_at('2018-07-06/w[1]', '2018-07-01', True, False)
    assert_at('2018-07-06/w[1]', '2018-07-03', True, False)
    # bug in diary
    assert_at('0/1w[1sun]', '2018-07-29', True, True)


def test_month():
    assert_at('2018-07-07/m[Sat]', '2018-07-07', True, True)
    assert_at('2018-07-07/m[2]', '2018-07-02', True, True)


def test_start_finish():
    p = Specification('2018-07-08/2d2018-07-08-2018-07-09')
    assert p.start == dt.date(2018, 7, 8)
    p.start = None
    assert p.start is None
    assert p.finish == dt.date(2018, 7, 9)
