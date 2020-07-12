
from . import profiles
from ..lib.inspect import read_package


def get_profiles():
    return dict(read_package(profiles))


def get_profile(name):
    return get_profiles()[name]
