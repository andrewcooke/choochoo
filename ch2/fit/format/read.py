
from .tokens import State, FileHeader, token_factory, Checksum
from ..profile.profile import read_profile


def tokens(log, data, types, messages, no_validate=False):
    state = State(log, types, messages)
    file_header = FileHeader(data)
    yield 0, file_header
    offset = len(file_header)
    file_header.validate(data, log, quiet=no_validate)
    while len(data) - offset > 2:
        token = token_factory(data[offset:], state)
        yield offset, token
        offset += len(token)
    checksum = Checksum(data[offset:])
    yield offset, checksum
    checksum.validate(data, log, quiet=no_validate)


def filtered_tokens(log, data, after=0, limit=-1, warn=False, no_validate=False, profile_path=None):

    types, messages = read_profile(log, warn=warn, profile_path=profile_path)

    def generator():
        for i, (offset, token) in enumerate(tokens(log, data, types, messages, no_validate=no_validate)):
            if i >= after and (limit < 0 or i - after < limit):
                yield i, offset, token

    return types, messages, generator()


def filtered_records(log, data, after=0, limit=-1, record_names=None, warn=False, no_validate=False, internal=False,
                     profile_path=None):

    types, messages, generator = filtered_tokens(log, data, after=after, limit=limit, warn=warn,
                                                 no_validate=no_validate, profile_path=profile_path)

    def filter():
        for i, offset, token in generator:
            if internal or token.is_user:
                record = token.parse(warn=warn)
                if not record_names or record.name in record_names:
                    yield record

    return types, messages, filter()
