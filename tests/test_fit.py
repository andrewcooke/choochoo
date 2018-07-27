
from logging import getLogger, basicConfig, DEBUG
from sys import stdout

from choochoo.fit.profile import read_profile


def test_profile():

    basicConfig(stream=stdout, level=DEBUG)
    log = getLogger()
    types, messages = read_profile(log, 'data/Profile.xlsx')

    cen = types['carry_exercise_name']
    print(cen.name, cen.base_type)
    for key, value in cen.items():
        print(key, value)

    session = messages['session']
    data = session['total_cycles']
    assert data.is_dynamic
    for field in data.dynamic_fields:
        assert field.name == 'sport'
    keys = ','.join('%s:%s' % (name, value) for name, value in sorted(data.dynamic.keys()))
    assert keys == 'sport:1,sport:11', keys

    workout_step = messages['workout_step']
    data = workout_step[4]
    assert data.name == 'target_value', data.name
    assert data.is_dynamic
    fields = ','.join(sorted(field.name for field in data.dynamic_fields))
    assert fields == 'duration_type,target_type', fields
    keys = ','.join('%s:%s' % (name, value) for name, value in sorted(data.dynamic.keys()))
    assert keys == 'duration_type:6,duration_type:7,duration_type:8,duration_type:9,duration_type:10,duration_type:11,duration_type:12,duration_type:13,target_type:0,target_type:1,target_type:3,target_type:4,target_type:11', keys
