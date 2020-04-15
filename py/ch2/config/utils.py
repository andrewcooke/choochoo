
from . import profile
from ..lib.inspect import read_package


def profiles():
    return dict(read_package(profile))


def get_profile(name):
    return profiles()[name]
