
from pickle import load

import openpyxl as xls
from pkg_resources import resource_stream

from .messages import Messages
from .support import NullableLog
from .types import Types

PROFILE = 'global-profile.pkl'


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
    # todo separate? (this is called a lot on repeated reads)
    if profile_path:
        _nlog, types, messages = read_profile(log, profile_path, warn=warn)
    else:
        types, messages = load_profile(log)
    log.debug('Read profile')
    with open(fit_path, 'rb') as input:
        data =input.read()
    return data, types, messages
