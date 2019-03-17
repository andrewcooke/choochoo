
from logging import getLogger

from .args import PATH, WARN
from ..fit.profile.profile import pickle_profile

log = getLogger(__name__)


def package_fit_profile(args, db):
    '''
## package-fit-profile

    > ch2 package-fit-profile data/sdk/Profile.xlsx

Parse the global profile and save the structures containing types and messages
to a pickle file that is distributed with this package.

This command is intended for internal use only.
    '''
    in_path, warn = args.file(PATH, rooted=False), args[WARN]
    pickle_profile(log, in_path, warn=warn)
