
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
