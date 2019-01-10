
from .tokens import State, FileHeader, token_factory, Checksum
from ..profile.profile import read_profile


def parse_data(log, data, types, messages, no_validate=False, max_delta_t=None):

    state = State(log, types, messages, max_delta_t=max_delta_t)

    def generator():
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

    return state, generator()


def filtered_tokens(log, data, after_bytes=None, after_records=None, limit_records=-1, warn=False, no_validate=False,
                    max_delta_t=None, profile_path=None):

    types, messages = read_profile(log, warn=warn, profile_path=profile_path)
    state, tokens = parse_data(log, data, types, messages, no_validate=no_validate, max_delta_t=max_delta_t)

    def generator():
        first_record = 0 if (after_records is None and after_bytes is None) else None
        for i, (offset, token) in enumerate(tokens):
            if first_record is None and ((after_records is not None and i >= after_records) or
                                         (after_bytes is not None and offset >= after_bytes)):
                first_record = i
            if first_record is not None and (limit_records < 0 or i - first_record < limit_records):
                yield i, offset, token

    return types, messages, generator()


def filtered_records(log, data, after_bytes=0, after_records=0, limit_records=-1, record_names=None, warn=False,
                     no_validate=False, internal=False, max_delta_t=None, profile_path=None, pipeline=None):

    if pipeline is None: pipeline = []
    types, messages = read_profile(log, warn=warn, profile_path=profile_path)
    state, tokens = parse_data(log, data, types, messages, no_validate=no_validate, max_delta_t=max_delta_t)

    def generator():
        first_record = 0 if (after_records is None and after_bytes is None) else None
        for i, (offset, token) in enumerate(tokens):
            if first_record is None and ((after_records is not None and i >= after_records) or
                                         (after_bytes is not None and offset >= after_bytes)):
                first_record = i
            record = token.parse_token(warn=warn)
            if state.accumulators: record = record.force(*pipeline)
            if (internal or token.is_user) and first_record is not None and \
                    (limit_records < 0 or i - first_record < limit_records) and \
                    (not record_names or record.name in record_names):
                if not state.accumulators: record = record.force(*pipeline)
                yield i, offset, record

    return types, messages, generator()
