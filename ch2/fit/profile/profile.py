
from os.path import join, dirname
from pickle import dump, load

import openpyxl as xls
from pkg_resources import resource_stream

from .messages import Messages
from .support import NullableLog
from .types import Types
from ...lib.args import PATH, WARN

PROFILE = 'global-profile.pkl'


def package_fit_profile(args, log):
    '''
# package-fit-profile

    ch2 package-fit-profile data/sdk/Profile.xlsx

Parse the global profile and save the structures containing types and messages
to a pickle file that is distributed with this package.

This command is intended for internal use only.
    '''
    in_path = args.file(PATH, index=0, rooted=False)
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


def read_profile(log, path, warn=False):
    nlog = NullableLog(log)
    wb = xls.load_workbook(path)
    types = Types(nlog, wb['Types'], warn=warn)
    messages = Messages(nlog, wb['Messages'], types, warn=warn)
    return nlog, types, messages


def load_profile(log):
    input = resource_stream(__name__, PROFILE)
    nlog, types, messages = load(input)
    nlog.set_log(log)
    return types, messages


def load_fit(log, fit_path, warn=False, profile_path=None):
    # todo separate?
    if profile_path:
        _nlog, types, messages = read_profile(log, profile_path, warn=warn)
    else:
        types, messages = load_profile(log)
    log.debug('Read profile')
    with open(fit_path, 'rb') as input:
        data =input.read()
    return data, types, messages
