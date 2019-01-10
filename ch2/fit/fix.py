
from .format.tokens import FileHeader, token_factory, Checksum, State
from .profile.profile import read_profile
from ..command.args import ADD_HEADER, mm, HEADER_SIZE, PROFILE_VERSION, PROTOCOL_VERSION, MIN_SYNC_CNT, \
    MAX_RECORD_LEN, MAX_DROP_CNT, MAX_BACK_CNT, MAX_FWD_LEN, FORCE, no, MAX_DELTA_T


def fix(log, data, add_header=False, drop=False, slices=None, warn=False, force=True, validate=True, profile_path=None,
        header_size=None, protocol_version=None, profile_version=None,
        min_sync_cnt=3, max_record_len=None, max_drop_cnt=1, max_back_cnt=3, max_fwd_len=200, max_delta_t=None):

    if not force:
        log.warn('%s means that data are not completely parsed' % no(FORCE))

    slices = parse_slices(log, slices)
    types, messages = read_profile(log, warn=warn, profile_path=profile_path)
    data = bytearray(data)

    log_data(log, 'Initial', data)

    if add_header:
        data = prepend_header(log, data, header_size, protocol_version, profile_version)

    if drop:
        slices = drop_data(log, State(log, types, messages, max_delta_t=max_delta_t), data, warn=warn, force=force,
                           min_sync_cnt=min_sync_cnt, max_record_len=max_record_len, max_drop_cnt=max_drop_cnt,
                           max_back_cnt=max_back_cnt, max_fwd_len=max_fwd_len)

    if slices:
        data = apply_slices(log, data, slices)

    data = header_and_checksums(log, data, State(log, types, messages, max_delta_t=max_delta_t),
                                header_size=header_size, protocol_version=protocol_version,
                                profile_version=profile_version)

    if validate:
        validate_data(log, data, State(log, types, messages, max_delta_t=max_delta_t), warn=warn, force=force)

    log_data(log, 'Final', data)

    return data


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


def log_data(log, title, data):
    log.info('%s Data ----------' % title)
    log.info('Length: %d bytes' % len(data))
    try:
        header = FileHeader(data)
        log.info('Header size: %d' % header.header_size)
        log.info('Protocol version: %d' % header.protocol_version)
        log.info('Profile version: %d' % header.profile_version)
    except Exception as e:
        log.info('Could not parse header: %s' % e)
    try:
        checksum = Checksum(data[-2:])
        log.info('Checksum: %d (0x%04x)' % (checksum.checksum, checksum.checksum))
    except Exception as e:
        log.info('Could not parse checksum: %s' % e)


def prepend_header(log, data, header_size, protocol_version, profile_version):

    log.info('Add Header ----------')

    header_size = set_default(log, HEADER_SIZE, header_size, 14)
    protocol_version = set_default(log, PROTOCOL_VERSION, protocol_version, 0x10)  # from FR35
    profile_version = set_default(log, PROFILE_VERSION, profile_version, 0x07de)  # from FR35

    data = bytearray([header_size] + [0] * (header_size - 1)) + data
    header = FileHeader(data)
    header.repair(data, log,
                  header_size=header_size, protocol_version=protocol_version, profile_version=profile_version)
    data[:len(header)] = header.data
    return data


def log_param(log, name, value):
    log.info('%s %s' % (mm(name), value))


def set_default(log, name, value, deflt):
    if value is None:
        value = deflt
    log_param(log, name, value)
    return value


def header_and_checksums(log, data, initial_state, header_size=None, protocol_version=None, profile_version=None):
    log.info('Header and Checksums ----------')
    log_param(log, HEADER_SIZE, header_size)
    log_param(log, PROTOCOL_VERSION, protocol_version)
    log_param(log, PROFILE_VERSION, profile_version)
    data = fix_header(log, data,
                      header_size=header_size, protocol_version=protocol_version, profile_version=profile_version)
    data = fix_checksum(log, data, initial_state.copy())
    data = fix_header(log, data)  # if length changed with checksum
    data = fix_checksum(log, data, initial_state.copy())  # if length changed
    return data


def fix_header(log, data, header_size=None, protocol_version=None, profile_version=None):
    try:
        header = FileHeader(data)
        # if these are undefined, use existing values (might be used if size changes)
        if protocol_version is None:
            protocol_version = header.protocol_version
        if profile_version is None:
            profile_version = header.profile_version
        prev_len = len(header)
        header.repair(data, log, header_size=header_size, protocol_version=protocol_version, profile_version=profile_version)
        data[:prev_len] = header.data
        return data
    except Exception as e:
        log.error(e)
        raise Exception('Error fixing header - maybe try %s' % mm(ADD_HEADER))


def fix_checksum(log, data, state):
    try:
        offset = len(FileHeader(data))
        while len(data) - offset > 2:
            token = token_factory(data[offset:], state)
            offset += len(token)
        if len(data) - offset < 2:
            n = offset + 2 - len(data)
            log.warning('Adding %d byte(s) for checksum' % n)
            data += bytearray([0] * n)
        checksum = Checksum(data[offset:])
        checksum.repair(data, log)
        data[-2:] = checksum.data
        return data
    except Exception as e:
        log.error(e)
        raise Exception('Error fixing checksum')


def apply_slices(log, data, slices):

    log.info('Slice ----------')
    log.info('Slices %s' % format_slices(slices))

    result = bytearray()
    for slice in slices:
        result += data[slice]
    log.info('Have %d bytes after slicing' % len(result))
    dropped = len(data) - len(result)
    if dropped:
        log.warning('Slicing decreased length by %d bytes' % dropped)

    return result


def validate_data(log, data, state, warn=False, force=True):

    log.info('Validation ----------')
    log_param(log, MAX_DELTA_T, state.max_delta_t)

    first_t = True
    try:
        file_header = FileHeader(data)
        file_header.validate(data, log)
        offset = len(file_header)
        while len(data) - offset > 2:
            token = token_factory(data[offset:], state)
            if first_t and state.timestamp:
                log.info('First timestamp: %s' % state.timestamp)
                first_t = False
            record = token.parse_token(warn=warn)
            if force:
                record.force()
            offset += len(token)
        log.info('Last timestamp:  %s' % state.timestamp)
        checksum = Checksum(data[offset:])
        checksum.validate(data, log)
        log.info('OK')
    except Exception as e:
        log.error(e)
        log.info('Validation failed')
        raise


def drop_data(log, initial_state, data, warn=False, force=True,
              min_sync_cnt=3, max_record_len=None, max_drop_cnt=1, max_back_cnt=3, max_fwd_len=200):

    log.info('Drop Data ----------')
    for (name, value) in [(MIN_SYNC_CNT, min_sync_cnt), (MAX_RECORD_LEN, max_record_len),
                          (MAX_DROP_CNT, max_drop_cnt), (MAX_BACK_CNT, max_back_cnt),
                          (MAX_FWD_LEN, max_fwd_len), (MAX_DELTA_T, initial_state.max_delta_t)]:
        log_param(log, name, value)

    slices = advance(log, initial_state, data, drop_count=0, initial_offset=0, warn=warn, force=force,
                     min_sync_cnt=min_sync_cnt, max_record_len=max_record_len, max_drop_cnt=max_drop_cnt,
                     max_back_cnt=max_back_cnt, max_fwd_len=max_fwd_len)
    log.info('Found slices %s' % format_slices(slices))
    return slices


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
        record = token.parse_token(warn=warn)
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
    initial_offsets_and_states = [(initial_offset, initial_state.copy())]
    offsets_and_states, complete = slurp(log, initial_state, data, initial_offset,
                                         warn=warn, force=force, max_record_len=max_record_len)
    if offsets_and_states:
        log.debug('%d: Read %d records; offset %d to %d' %
                  (drop_count, len(offsets_and_states), initial_offset, offsets_and_states[-1][0]))
    else:
        log.debug('%d: Did not read any records' % drop_count)
    offsets_and_states = initial_offsets_and_states + offsets_and_states
    if complete:
        # use explicit offset rather than open interval because need to drop final checksum
        if len(offsets_and_states) > 1:
            return [slice( offsets_and_states[0][0], offsets_and_states[-1][0])]
        else:
            return []
    if drop_count and len(offsets_and_states) < min_sync_cnt:  # failing to sync on first read is OK
        raise Backtrack('Failed to sync at offset %d' % initial_offset)
    if drop_count >= max_drop_cnt:
        raise Backtrack('No more drops')
    for delta in range(1, max_fwd_len):
        for back_cnt in range(1, min(max_back_cnt + 1, len(offsets_and_states))):
            offset, state = offsets_and_states[-back_cnt]
            log.debug('Searching forwards from offset %d after dropping %d records' % (offset, back_cnt-1))
            if offset + delta >= len(data):  # > for when a delta of 0 would have done
                log.info('Exhausted data')
                return [slice(initial_offset, len(data)-2)]
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

