from logging import getLogger

from .records import restrict_names
from .tokens import State, FileHeader, token_factory, Checksum
from ..profile.profile import read_profile
from ...lib.data import tohex

log = getLogger(__name__)


def parse_data(data, types, messages, no_validate=False, max_delta_t=None):

    state = State(types, messages, max_delta_t=max_delta_t)

    def generator():
        offset = 0
        try:
            file_header = FileHeader(data[offset:])
            yield offset, file_header
            offset = len(file_header)
            file_header.validate(data, log, quiet=no_validate)
            while len(data) - offset > 2:
                token = token_factory(data[offset:], state)
                yield offset, token
                offset += len(token)
            checksum = Checksum(data[offset:])
            yield offset, checksum
            checksum.validate(data, log, quiet=no_validate)
        except Exception as e:
            log.warning('"%s" at offset %d' % (e, offset))
            dump(data, offset)
            raise

    return state, generator()


def dump(data, offset, rows=3, blocks=6, block=4):
    for row in range(rows):
        line = '%06d' % offset
        for b in range(blocks):
            line += ' '
            line += tohex(data[offset:offset+block])
            offset += block
        log.info(line)
        if offset >= len(data): return


def filtered_tokens(data,
                    after_bytes=None, limit_bytes=-1, after_records=None, limit_records=-1,
                    warn=False, no_validate=False, max_delta_t=None, profile_path=None):

    types, messages = read_profile(log, warn=warn, profile_path=profile_path)
    state, tokens = parse_data(data, types, messages, no_validate=no_validate, max_delta_t=max_delta_t)

    def generator():
        first_record = 0 if (after_records is None) else None
        first_bytes = 0 if (after_bytes is None) else None
        for i, (offset, token) in enumerate(tokens):
            if (first_record is None and (after_records is not None and i >= after_records)) or \
                    (first_bytes is None and (after_bytes is not None and offset >= after_bytes)):
                first_record = i
                first_bytes = offset
            if (first_record is not None and (limit_records < 0 or i - first_record < limit_records)) and \
                    (first_bytes is not None and (limit_bytes < 0 or offset - first_bytes < limit_bytes)):
                yield i, offset, token

    return types, messages, generator()


def filtered_records(data,
                     after_bytes=None, limit_bytes=-1, after_records=None, limit_records=-1,
                     record_names=None, field_names=None,
                     warn=False, no_validate=False, internal=False, max_delta_t=None,
                     profile_path=None, pipeline=None):

    if pipeline is None: pipeline = []
    if field_names: pipeline.append(restrict_names(field_names))
    types, messages = read_profile(log, warn=warn, profile_path=profile_path)
    state, tokens = parse_data(data, types, messages, no_validate=no_validate, max_delta_t=max_delta_t)

    def generator():
        first_record = 0 if (after_records is None) else None
        first_bytes = 0 if (after_bytes is None) else None
        for i, (offset, token) in enumerate(tokens):
            if (first_record is None and (after_records is not None and i >= after_records)) or \
                    (first_bytes is None and (after_bytes is not None and offset >= after_bytes)):
                first_record = i
                first_bytes = offset
            record = token.parse_token(warn=warn)
            if state.accumulators: record = record.force(*pipeline)
            if (internal or token.is_user) and (not record_names or record.name in record_names) and \
                    (first_record is not None and (limit_records < 0 or i - first_record < limit_records)) and \
                    (first_bytes is not None and (limit_bytes < 0 or offset - first_bytes < limit_bytes)):
                if not state.accumulators: record = record.force(*pipeline)
                yield i, offset, record

    return types, messages, generator()
