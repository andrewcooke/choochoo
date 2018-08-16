
from logging import getLogger, basicConfig, DEBUG
from sys import stdout

from choochoo.fit.profile.fields import DynamicField
from choochoo.fit.profile.profile import read_profile
from choochoo.fit.records import no_names, append_units, no_bad_values, fix_degrees, chain
from choochoo.fit.summary import summarize
from choochoo.fit.tokens import parse_all


def test_profile():

    basicConfig(stream=stdout, level=DEBUG)
    log = getLogger()
    nlog, types, messages = read_profile(log, '/home/andrew/project/ch2/choochoo/data/sdk/Profile.xlsx')

    cen = types.profile_to_type('carry_exercise_name')
    assert cen.profile_to_internal('farmers_walk') == 1

    session = messages.profile_to_message('session')
    field = session.profile_to_field('total_cycles')
    assert isinstance(field, DynamicField), type(field)
    for name in field.references:
        assert name == 'sport'

    workout_step = messages.profile_to_message('workout_step')
    field = workout_step.number_to_field(4)
    assert field.name == 'target_value', field.name
    fields = ','.join(sorted(field.references))
    assert fields == 'duration_type,target_type', fields


def test_decode():

    basicConfig(stream=stdout, level=DEBUG)
    log = getLogger()
    for record in parse_all(log, '/home/andrew/project/ch2/choochoo/data/test/personal/2018-07-26-rec.fit',
                            profile_path='/home/andrew/project/ch2/choochoo/data/sdk/Profile.xlsx'):
        print(record.into(tuple, filter=chain(no_names, append_units, no_bad_values, fix_degrees)))


def test_dump():

    basicConfig(stream=stdout, level=DEBUG)
    log = getLogger()
    summarize(log, '/home/andrew/project/ch2/choochoo/data/test/personal/2018-07-30-rec.fit',
              profile_path='/home/andrew/project/ch2/choochoo/data/sdk/Profile.xlsx')


def test_developer():

    basicConfig(stream=stdout, level=DEBUG)
    log = getLogger()
    summarize(log, '/home/andrew/project/ch2/choochoo/data/test/sdk/DeveloperData.fit',
              profile_path='/home/andrew/project/ch2/choochoo/data/sdk/Profile.xlsx')
