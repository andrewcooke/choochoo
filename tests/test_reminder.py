
from choochoo.reminder import Specification, DateOrdinals


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
    assert_str(Specification('m[2Tu]'), '0/1m[2tu]')
    assert_str(Specification('2m[2Tu]'), '0/2m[2tu]')
    assert_str(Specification('1/2m[2Tu]'), '1/2m[2tu]')
    assert_str(Specification('m[2Tu]1970-01-01-1970-12-31'), '0/1m[2tu]1970-01-01-1970-12-31')
    assert_str(Specification('2018-07-05/5d[]'), '2/5d[1]')
    assert_str(Specification('d2018-07-05'), '0/1d[1]2018-07-05')
    # others
    assert_str(Specification('1/2w[1]2018-01-01-'), '1/2w[1]2018-01-01-')
    assert_str(Specification('1/2w[Mo,2,3]-1970-01-01'), '1/2w[1mo,2,3]-1970-01-01')
    # some errors
    assert_bad(Specification, '1/2[]2018-01-01-')
    assert_bad(Specification, '1/2w[1d]2018-01-01-')


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
    assert_at('2d[Fr]', '2018-07-06', True, True)
    assert_at('2d[1Fr]', '2018-07-06', True, True)
    assert_at('2d[2Fr]', '2018-07-06', True, False)
    assert_at('2d[Mo]', '2018-07-06', True, False)


def test_week():
    assert_at('2018-07-06/w[Fr]', '2018-07-06', True, True)
    assert_at('2018-07-06/w[1]', '2018-07-02', True, True)


def test_month():
    assert_at('2018-07-07/m[Sa]', '2018-07-07', True, True)
    assert_at('2018-07-07/m[2]', '2018-07-02', True, True)
