
from ..profile.profile import load_fit
from .tokens import State, FileHeader, token_factory, Checksum


def tokens(log, data, types, messages):
    state = State(log, types, messages)
    file_header = FileHeader(data)
    yield 0, file_header
    offset = len(file_header)
    file_header.validate(data)
    while len(data) - offset > 2:
        token = token_factory(data[offset:], state)
        yield offset, token
        offset += len(token)
    checksum = Checksum(data)
    yield offset, checksum
    checksum.validate(offset)


def filtered_tokens(log, fit_path, after=0, limit=-1, profile_path=None):
    data, types, messages = load_fit(log, fit_path, profile_path=profile_path)

    def generator():
        for i, (offset, token) in enumerate(tokens(log, data, types, messages)):
            if i >= after and (limit < 0 or i - after < limit):
                yield i, offset, token

    return data, types, messages, generator()


def filtered_records(log, fit_path, after=0, limit=-1, profile_path=None):
    data, types, messages = load_fit(log, fit_path, profile_path=profile_path)

    def generator():
        for i, (offset, token) in enumerate((offset, token)
                                            for (offset, token) in tokens(log, data, types, messages)
                                            if token.is_user):
            if i >= after and (limit < 0 or i - after < limit):
                yield token.parse()

    return data, types, messages, generator()
