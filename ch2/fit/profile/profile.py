
from os.path import join, dirname
from pickle import load, dump

import openpyxl as xls
from pkg_resources import resource_stream

from .messages import Messages
from .support import NullableLog
from .types import Types

PROFILE_NAME = 'global-profile.pkl'
PROFILE = []


def read_profile(log, path, warn=False):
    nlog = NullableLog(log)
    wb = xls.load_workbook(path)
    types = Types(nlog, wb['Types'], warn=warn)
    messages = Messages(nlog, wb['Messages'], types, warn=warn)
    return nlog, types, messages


def load_profile(log):
    if not PROFILE:
        log.debug('Unpickling profile')
        input = resource_stream(__name__, PROFILE_NAME)
        PROFILE.append(load(input))
        PROFILE[0][0].set_log(log)
    return PROFILE[0][1:]


def load_fit(log, fit_path, warn=False, profile_path=None):
    if profile_path:
        log.debug('Reading profile from %s' % profile_path)
        _nlog, types, messages = read_profile(log, profile_path, warn=warn)
    else:
        types, messages = load_profile(log)
    log.debug('Read profile')
    with open(fit_path, 'rb') as input:
        data = input.read()
    return data, types, messages


def pickle_profile(log, in_path, warn=False):
    log.info('Reading from %s' % in_path)
    nlog, types, messages = read_profile(log, in_path, warn=warn)
    out_path = join(dirname(__file__), PROFILE_NAME)
    nlog.set_log(None)
    log.info('Writing to %s' % out_path)
    with open(out_path, 'wb') as output:
        dump((nlog, types, messages), output)
    # test loading
    log.info('Test loading from %r' % PROFILE_NAME)
    log.info('Loaded %s, %s' % load_profile(log))
