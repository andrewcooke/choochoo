
from logging import getLogger, basicConfig, DEBUG
from sys import stdout

from choochoo.fit.profile import read_profile


def test_profile():

    basicConfig(stream=stdout, level=DEBUG)
    log = getLogger()
    types, messages = read_profile(log, 'data/Profile.xlsx')

    cen = types.profile_to_type('carry_exercise_name')
    assert cen.profile_to_internal('farmers_walk') == 1

    session = messages.profile_to_message('session')
    field = session.profile_to_field('total_cycles')
    assert field.is_dynamic
    for ref in field.references:
        assert ref.name == 'sport'
    keys = ','.join('%s:%s' % (name, value) for name, value in sorted(field.dynamic.keys()))
    assert keys == 'sport:1,sport:11', keys

    workout_step = messages.profile_to_message('workout_step')
    field = workout_step.internal_to_field(4)
    assert field.name == 'target_value', field.name
    assert field.is_dynamic
    fields = ','.join(sorted(field.name for field in field.references))
    assert fields == 'duration_type,target_type', fields
    keys = ','.join('%s:%s' % (name, value) for name, value in sorted(field.dynamic.keys()))
    assert keys == 'duration_type:6,duration_type:7,duration_type:8,duration_type:9,duration_type:10,duration_type:11,duration_type:12,duration_type:13,target_type:0,target_type:1,target_type:3,target_type:4,target_type:11', keys
