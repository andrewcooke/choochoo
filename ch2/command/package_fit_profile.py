
from os.path import join, dirname
from pickle import dump

from .args import PATH, WARN
from ..fit.profile.profile import read_profile, PROFILE, load_profile


def package_fit_profile(args, log, db):
    '''
# package-fit-profile

    ch2 package-fit-profile data/sdk/Profile.xlsx

Parse the global profile and save the structures containing types and messages
to a pickle file that is distributed with this package.

This command is intended for internal use only.
    '''
    in_path = args.file(PATH, rooted=False)
    log.info('Reading from %s' % in_path)
    nlog, types, messages = read_profile(log, in_path, warn=args[WARN])
    out_path = join(dirname(__file__), PROFILE)
    nlog.set_log(None)
    log.info('Writing to %s' % out_path)
    with open(out_path, 'wb') as output:
        dump((nlog, types, messages), output)
    # test loading
    log.info('Test loading from %r' % PROFILE)
    log.info('Loaded %s, %s' % load_profile(log))
