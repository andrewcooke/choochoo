
from .format.tokens import FileHeader, token_factory, Checksum, State
from .profile.profile import read_profile


def fix(log, data, drop=False, slices=None, warn=False, force=True, validate=False, profile_path=None,
        min_sync_cnt=3, max_record_len=None, max_drop_cnt=1, max_back_cnt=3, max_fwd_len=200):

    from ch2.command.fix_fit import format_slices

    types, messages = read_profile(log, warn=warn, profile_path=profile_path)

    if drop:
        slices = advance(log, State(log, types, messages), data, warn=warn, force=force,
                         min_sync_cnt=min_sync_cnt, max_record_len=max_record_len, max_drop_cnt=max_drop_cnt,
                         max_back_cnt=max_back_cnt, max_fwd_len=max_fwd_len)
        log.info('Dropped data to find slices: %s' % format_slices(slices))
    if slices:
        data = apply_slices(log, data, slices)
        log.info('Have %d bytes after slicing' % len(data))
    data = fix_header(log, data)
    data = fix_checksum(log, data, State(log, types, messages))
    data = fix_header(log, data)  # if length changed with checksum
    if validate:
        validate_data(log, data, State(log, types, messages), warn=warn, force=force)
    return data


def fix_header(log, data):
    try:
        header = FileHeader(data)
        header.repair(data, log)
        data[:len(header)] = header.data
        return data
    except:
        log.error('Could not parse header so pre-pending new header')
        # todo - need protocol version etc
        raise NotImplementedError()


def fix_checksum(log, data, state):
    *_, (_, checksum) = offset_tokens(state.copy(), data, warn=False, force=False)
    if not isinstance(checksum, Checksum):
        data += [0, 0]
        return fix_checksum(log, data, state)
    checksum.repair(data, log)
    data[-2:] = checksum.data
    return data


def apply_slices(log, data, slices):
    result = bytearray()
    for slice in slices:
        result += data[slice]
    dropped = len(data) - len(result)
    if dropped:
        log.warn('Slicing decreased length by %d bytes' % dropped)
    return result


def validate_data(log, data, state, warn=False, force=True):
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
    checksum = Checksum(data)
    checksum.validate(offset, log)
    log.info('Validated')


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
    # todo - need to support missing checksums
    checksum = Checksum(data)
    offset += len(checksum)
    yield offset, checksum


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
    if complete:
        return [slice(initial_offset, None)]
    if drop_count and len(offsets_and_states) < min_sync_cnt:  # failing to sync on first read is OK
        raise Backtrack('Failed to sync at offset %d' % initial_offset)
    if drop_count >= max_drop_cnt:
        raise Backtrack('No more drops')
    for back_cnt in range(1, min(max_back_cnt + 1, len(offsets_and_states))):
        offset, state = offsets_and_states[-back_cnt]
        log.info('Searching forwards from offset %d after dropping %d records' % (offset, back_cnt-1))
        for delta in range(1, max_fwd_len):
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

