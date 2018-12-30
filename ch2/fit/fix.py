
from collections import deque

from ch2.command.args import ADD_HEADER, mm, HEADER_SIZE, PROFILE_VERSION, PROTOCOL_VERSION
from .format.tokens import FileHeader, token_factory, Checksum, State
from .profile.profile import read_profile


def fix(log, data, add_header=False, drop=False, slices=None, warn=False, force=True, validate=True, profile_path=None,
        header_size=None, protocol_version=None, profile_version=None,
        min_sync_cnt=3, max_record_len=None, max_drop_cnt=1, max_back_cnt=3, max_fwd_len=200):

    header_size = set_default(log, add_header, HEADER_SIZE, header_size, 14)
    protocol_version = set_default(log, add_header, PROTOCOL_VERSION, protocol_version, 0x10)  # from FR35
    profile_version = set_default(log, add_header, PROFILE_VERSION, profile_version, 0x07de)  # from FR35

    slices = parse_slices(log, slices)
    types, messages = read_profile(log, warn=warn, profile_path=profile_path)
    data = bytearray(data)

    if add_header:
        data = prepend_header(log, data, header_size, protocol_version, profile_version)

    if drop:
        slices = advance(log, State(log, types, messages), data, warn=warn, force=force,
                         min_sync_cnt=min_sync_cnt, max_record_len=max_record_len, max_drop_cnt=max_drop_cnt,
                         max_back_cnt=max_back_cnt, max_fwd_len=max_fwd_len)
        log.info('Dropped data to find slices: %s' % format_slices(slices))

    if slices:
        data = apply_slices(log, data, slices)
        log.info('Have %d bytes after slicing' % len(data))
        data += b'\0\0'
        log.warning('Appended blank checksum')

    data = fix_header(log, data)
    data = fix_checksum(log, data)
    data = fix_header(log, data)  # if length changed with checksum

    if validate:
        validate_data(log, data, State(log, types, messages), warn=warn, force=force)

    return data


def set_default(log, required, name, value, deflt):
    if required and value is None:
        log.warning('Setting %s to %d' % (mm(name), deflt))
        return deflt
    else:
        return value


def parse_slices(log, slices):
    if not slices:
        return None
    parsed = [parse_slice(slice) for slice in slices.split(',')]
    if parsed and parsed[-1].stop is None:
        parsed[-1] = slice(parsed[-1].start, -2)
    log.debug('Parsed "%s" as "%s"' % (slices, format_slices(parsed)))
    return parsed


def parse_slice(s):
    start, stop = (parse_offset(offset) for offset in s.split(':'))
    return slice(start, stop)


def parse_offset(offset):
    if offset:
        return int(offset)
    else:
        return None


def format_slices(slices):
    return ','.join(format_slice(slice) for slice in slices)


def format_slice(slice):
    return '%s:%s' % (format_offset(slice.start), format_offset(slice.stop))


def format_offset(offset):
    return '' if offset in (0, None) else str(offset)


def prepend_header(log, data, header_size, protocol_version, profile_version):
    log.warning('Prepending file header of length %d' % header_size)
    log_header_settings(log, data, header_size, protocol_version, profile_version)
    data = bytearray([0] * header_size) + data
    header = FileHeader(data)
    header.repair(data, log,
                  header_size=header_size, protocol_version=protocol_version, profile_version=profile_version)
    data[:len(header)] = header.data
    return data


def log_header_settings(log, data, header_size, protocol_version, profile_version):
    try:
        header = FileHeader(data)
        log.info('Header size (prev/new): %d/%d' % (header.header_size, header_size))
        log.info('Protocol version (prev/new): %d/%d' % (header.protocol_version, protocol_version))
        log.info('Profile version (prev/new): %d/%d' % (header.profile_version, profile_version))
    except:
        pass


def fix_header(log, data):
    try:
        header = FileHeader(data)
        header.repair(data, log)
        data[:len(header)] = header.data
        return data
    except Exception as e:
        log.error(e)
        raise Exception('Error fixing header - maybe try %s' % mm(ADD_HEADER))


def fix_checksum(log, data):
    try:
        checksum = Checksum(data[-2:])
        checksum.repair(data, log)
        data[-2:] = checksum.data
        return data
    except Exception as e:
        log.error(e)
        raise Exception('Error fixing checksum')


def apply_slices(log, data, slices):
    result = bytearray()
    for slice in slices:
        result += data[slice]
    dropped = len(data) - len(result)
    if dropped:
        log.warning('Slicing decreased length by %d bytes' % dropped)
    return result


def validate_data(log, data, state, warn=False, force=True):
    try:
        file_header = FileHeader(data)
        file_header.validate(data, log)
        offset = len(file_header)
        while len(data) - offset > 2:
            token = token_factory(data[offset:], state)
            if token.is_user:
                record = token.parse(warn=warn)
                if force:
                    record.force()
            offset += len(token)
        checksum = Checksum(data[offset:])
        checksum.validate(data, log)
        log.info('Validated')
    except Exception as e:
        log.error(e)
        log.info('Validation failed')
        raise


def offset_tokens(state, data, offset=0, warn=False, force=True):
    '''
    this yields the offsets *after* the tokens (unlike tokens() in the read module).
    '''
    if not offset:
        file_header = FileHeader(data)
        offset = len(file_header)
        yield offset, file_header
    while len(data) - offset > 2:
        token = token_factory(data[offset:], state)
        if token.is_user:
            record = token.parse(warn=warn)
            if force:
                record.force()
        offset += len(token)
        yield offset, token
    # if we're here then there are 2 or less bytes remaining
    if len(data) - offset != 2:
        raise Exception('Misaligned checksum')


def slurp(log, state, data, initial_offset, warn=False, force=True, max_record_len=None):
    '''
    read as much as possible starting at the given offset.

    return offsets of valid tokens and a flag indicating if all data were read.
    '''
    offsets_and_states = []
    offset = initial_offset
    try:
        for offset, token in offset_tokens(state, data, initial_offset, warn=warn, force=force):
            if max_record_len and len(token) > max_record_len:
                log.info('Record too large (%d > %d) at offset %d' % (len(token), max_record_len, offset))
                return offsets_and_states, False
            offsets_and_states.append((offset, state.copy()))
        log.info('Read complete from %d' % initial_offset)
        return offsets_and_states, True
    except Exception as e:
        log.debug('%s at %d' % (e, offset))
        log.debug('Reading from offset %s found %d tokens before %d' %
                  (initial_offset, len(offsets_and_states), offset))
        return offsets_and_states, False


class Backtrack(Exception): pass


def advance(log, initial_state, data, drop_count=0, initial_offset=0, warn=False, force=True,
            min_sync_cnt=3, max_record_len=None, max_drop_cnt=1, max_back_cnt=3, max_fwd_len=200):
    '''
    try to synchronize on the stream and then read as much as possible.  if reading later fails,
    then try recurse if not at limit; if that fails, backtrack a record and try again.

    finally return the offsets used.

    "synchronize" means progressively discard data until some number of records smaller than
    some length can be read.
    '''
    offsets_and_states, complete = slurp(log, initial_state, data, initial_offset,
                                         warn=warn, force=force, max_record_len=max_record_len)
    if offsets_and_states:
        log.debug('%d: Read %d records; offset %d to %d' %
                  (drop_count, len(offsets_and_states), initial_offset, offsets_and_states[-1][0]))
    else:
        log.debug('%d: Did not read any records' % drop_count)
    offsets_and_states = [(0, initial_state)] + offsets_and_states
    if complete:
        # use explicit offset rather than open interval because need to drop final checksum
        return [slice(initial_offset, offsets_and_states[-1][0])]
    if drop_count and len(offsets_and_states) < min_sync_cnt:  # failing to sync on first read is OK
        raise Backtrack('Failed to sync at offset %d' % initial_offset)
    if drop_count >= max_drop_cnt:
        raise Backtrack('No more drops')
    for back_cnt in range(1, min(max_back_cnt + 1, len(offsets_and_states))):
        offset, state = offsets_and_states[-back_cnt]
        log.info('Searching forwards from offset %d after dropping %d records' % (offset, back_cnt-1))
        for delta in range(1, max_fwd_len):
            if offset + delta >= len(data):  # > for when a delta of 0 would have done
                log.info('Exhausted data')
                return [slice(initial_offset, offset)]
            else:
                try:
                    log.debug('%d: Retrying (drop %d, skip %d) at offset %d' %
                              (drop_count, back_cnt-1, delta, offset+delta))
                    slices = advance(log, state.copy(), data, drop_count+1, offset+delta,
                                     min_sync_cnt=min_sync_cnt, max_record_len=max_record_len,
                                     max_drop_cnt=max_drop_cnt, max_fwd_len=max_fwd_len)
                    return [slice(initial_offset, offset)] + slices
                except Backtrack as e:
                    log.debug('%d: Backtrack at (drop %d, skip %d): "%s"' % (drop_count, back_cnt, delta, e))
    raise Backtrack('Search exhausted at %d' % initial_offset)

