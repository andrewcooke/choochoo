
import datetime as dt

from ch2.lib.schedule import Schedule, DateOrdinals
from ch2.lib.date import to_date


def assert_str(x1, s):
    s1 = str(x1)
    assert s1 == s, '%s != %s' % (s1, s)
    x2 = Schedule(s1)
    s2 = str(x2)
    assert s1 == s2, 'Not idempotent:  %s != %s' % (s1, s2)


def assert_bad(f, *args):
    ok = True
    try:
        f(*args)
    except:
        ok = False
    assert not ok, '%s %s' % (f, args)


def test_specification():
    # from the spec doc
    assert_str(Schedule('m[2Tue]'), 'm[2tue]')
    assert_str(Schedule('2m[2Tue]'), '2m[2tue]')
    assert_str(Schedule('1/2m[2Tue]'), '1/2m[2tue]')
    assert_str(Schedule('m[2Tue]1970-01-01-1970-12-31'), 'm[2tue]1970-01-01-1970-12-31')
    assert_str(Schedule('2018-07-05/5d[]'), '2/5d')
    assert_str(Schedule('d2018-07-05'), '2018-07-05')
    # others
    assert_str(Schedule('1/2w[1]2018-01-01-'), '1/2w[1]2018-01-01-')
    assert_str(Schedule('1/2w[Mon,2,3]-1970-01-01'), '1/2w[mon,2,3]-1970-01-01')
    # some errors
    assert_bad(Schedule, '1/2[]2018-01-01-')   # must specify type
    assert_bad(Schedule, '1/2w[1d]2018-01-01-')  # no longer support type in location
    # some additional shortcuts for easier config
    assert_str(Schedule('-2019-10-07'), '-2019-10-07')
    assert_str(Schedule('2019-10-07-'), '2019-10-07-')
    assert_str(Schedule('2019-10-07'), '2019-10-07')


def assert_at(spec, date, UNUSED, at_location):
    date = to_date(date)
    frame = Schedule(spec).frame()
    assert frame.at_location(date) == at_location, '%s %s' % (spec, date)


def test_day():
    assert_at('d', '2018-07-06', True, True)
    assert_at('d', '2018-07-07', True, True)
    assert_at('2d', '2018-07-06', True, True)
    assert_at('2d', '2018-07-07', False, True)
    assert_at('2d[1]', '2018-07-06', True, True)
    assert_at('2d[2]', '2018-07-06', True, False)
    assert_at('2d[3]', '2018-07-06', True, False)
    assert_at('2d[1]', '2018-07-07', False, False)
    assert_at('2d[2]', '2018-07-07', False, True)
    assert_at('2d[Fri]', '2018-07-06', True, True)
    assert_at('2d[Mon]', '2018-07-06', True, False)
    assert_at('2d[Fri]2018-07-06', '2018-07-06', True, True)
    assert_at('2d[Fri]2018-07-07', '2018-07-06', False, False)
    assert_at('2d[Fri]2018-07-06-2018-07-07', '2018-07-06', True, True)
    assert_at('2d[Fri]2018-07-07-2018-07-08', '2018-07-06', False, False)
    assert_at('2d[Fri]2018-07-05-2018-07-06', '2018-07-06', False, False)
    assert_at('2018-10-10/3d[1,fri]', '2018-10-10', True, True)
    assert_at('2018-10-10/3d[1,fri]', '2018-10-11', False, False)
    assert_at('2018-10-10/3d[1,fri]', '2018-10-12', False, True)


def test_week():
    assert_at('2018-07-06/w[Fri]', '2018-07-06', True, True)
    assert_at('2018-07-06/w[Fri]', '2018-07-05', True, False)
    assert_at('2018-07-06/w[Fri]', '2018-07-07', True, False)
    assert_at('2018-07-06/w[1]', '2018-07-02', True, True)
    assert_at('2018-07-06/w[1]', '2018-07-01', True, False)
    assert_at('2018-07-06/w[1]', '2018-07-03', True, False)
    assert_at('2018-07-06/w', '2018-07-02', True, True)
    assert_at('2018-07-06/w', '2018-07-01', True, True)
    assert_at('2018-07-06/w', '2018-07-03', True, True)
    # bug in diary
    assert_at('0/1w[1sun]', '2018-07-29', True, True)


def test_month():
    assert_at('m[Sat]', '2018-07-07', True, True)
    assert_at('m[2]', '2018-07-02', True, True)
    assert_at('m[2]', '2018-07-01', True, False)
    assert_at('m', '2018-07-02', True, True)
    # todo - numbering is different for months.  "2nd sunday" may not be in 2nd week.
    assert_at('m[1sat]', '2018-09-01', True, True)
    assert_at('m[1sun]', '2018-09-02', True, True)
    assert_at('m[1mon]', '2018-09-03', True, True)
    assert_at('m[1fri]', '2018-09-07', True, True)
    assert_at('m[2sat]', '2018-09-08', True, True)


def test_year():
    assert_at('2018-07-07/y', '2018-07-02', True, True)


def test_start_finish():
    p = Schedule('2018-07-08/2d2018-07-08-2018-07-09')
    assert p.start == dt.date(2018, 7, 8)
    p.start = None
    assert p.start is None
    assert p.finish == dt.date(2018, 7, 9)


def test_ordinals():
    d = dt.date(2018, 7, 25)
    o = DateOrdinals(d)
    assert o.dow == 3, o.dow  # wednesday


def test_frame_start():
    s = Schedule('2018-01-01/2y')
    assert s.frame().start_of_frame('2018-01-02') == to_date('2018-01-01')
    assert s.frame().start_of_frame('2017-01-02') == to_date('2016-01-01')
