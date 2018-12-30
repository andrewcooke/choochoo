
from .tokens import State, FileHeader, token_factory, Checksum
from ..profile.profile import read_fit, read_profile


def tokens(log, data, types, messages, no_header=False):
    state = State(log, types, messages)
    file_header = FileHeader(data)
    yield 0, file_header
    offset = len(file_header)
    file_header.validate(data, log, quiet=no_header)
    while len(data) - offset > 2:
        token = token_factory(data[offset:], state)
        yield offset, token
        offset += len(token)
    checksum = Checksum(data[offset:])
    yield offset, checksum
    checksum.validate(data, log, quiet=no_header)


def filtered_tokens(log, fit_path, after=0, limit=-1, warn=False, no_header=False, profile_path=None):

    types, messages = read_profile(log, warn=warn, profile_path=profile_path)
    data = read_fit(log, fit_path)

    def generator():
        for i, (offset, token) in enumerate(tokens(log, data, types, messages, no_header=no_header)):
            if i >= after and (limit < 0 or i - after < limit):
                yield i, offset, token

    return data, types, messages, generator()


def filtered_records(log, fit_path, after=0, limit=-1, records=None, warn=False, no_header=False, profile_path=None):

    types, messages = read_profile(log, warn=warn, profile_path=profile_path)
    data = read_fit(log, fit_path)

    def generator():
        for i, (offset, token) in enumerate((offset, token)
                                            for (offset, token) in tokens(log, data, types, messages,
                                                                          no_header=no_header)
                                            if token.is_user):
            if i >= after and (limit < 0 or i - after < limit):
                record = token.parse(warn=warn)
                if not records or record.name in records:
                    yield record

    return data, types, messages, generator()
