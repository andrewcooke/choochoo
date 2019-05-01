
from os.path import join, dirname
from pickle import load, dump

import openpyxl as xls
from pkg_resources import resource_stream

from ch2 import PACKAGE_FIT_PROFILE
from .messages import Messages
from .support import NullableLog
from .types import Types

PROFILE_NAME = 'global-profile.pkl'
PROFILE = []

# todo - remove log from here (and docs)

def read_external_profile(log, path, warn=False):
    nlog = NullableLog(log)
    wb = xls.load_workbook(path)
    types = Types(nlog, wb['Types'], warn=warn)
    messages = Messages(nlog, wb['Messages'], types, warn=warn)
    return nlog, types, messages


def read_internal_profile(log):
    if not PROFILE:
        log.debug('Unpickling profile')
        try:
            input = resource_stream(__name__, PROFILE_NAME)
            PROFILE.append(load(input))
            input.close()
        except FileNotFoundError:
            log.warning('There was a problem reading the pickled profile.')
            log.warning('If you installed via pip then please create an issue at')
            log.warning('https://github.com/andrewcooke/choochoo for support.')
            log.warning('If you installed via git please see `ch2 help %s`' % PACKAGE_FIT_PROFILE)
            raise Exception('Could not read %s (see log for more details)' % PROFILE_NAME)
        PROFILE[0][0].set_log(log)
    return PROFILE[0][1:]


def read_profile(log, warn=False, profile_path=None):
    if profile_path:
        log.debug('Reading profile from %s' % profile_path)
        _nlog, types, messages = read_external_profile(log, profile_path, warn=warn)
    else:
        types, messages = read_internal_profile(log)
    log.debug('Read profile')
    return types, messages


def read_fit(log, fit_path):
    log.debug('Reading fit file from %s' % fit_path)
    with open(fit_path, 'rb') as input:
        return input.read()


def pickle_profile(log, in_path, warn=False):
    log.info('Reading from %s' % in_path)
    nlog, types, messages = read_external_profile(log, in_path, warn=warn)
    out_path = join(dirname(__file__), PROFILE_NAME)
    nlog.set_log(None)
    log.info('Writing to %s' % out_path)
    with open(out_path, 'wb') as output:
        dump((nlog, types, messages), output)
    # test loading
    log.info('Test loading from %r' % PROFILE_NAME)
    log.info('Loaded %s, %s' % read_internal_profile(log))
