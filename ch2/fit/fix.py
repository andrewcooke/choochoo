
import datetime as dt
from logging import getLogger

from .format.tokens import FileHeader, token_factory, Checksum, State
from .profile.profile import read_profile
from ..commands.args import ADD_HEADER, mm, HEADER_SIZE, PROFILE_VERSION, PROTOCOL_VERSION, MIN_SYNC_CNT, \
    MAX_RECORD_LEN, MAX_DROP_CNT, MAX_BACK_CNT, MAX_FWD_LEN, MAX_DELTA_T
from ..lib.date import format_time, format_seconds

log = getLogger(__name__)


def fix(data, warn=False,
        add_header=False, drop=False, slices=None, start=None, fix_header=False, fix_checksum=False, force=True,
        validate=True, header_size=None, protocol_version=None, profile_version=None, min_sync_cnt=3,
        max_record_len=None, max_drop_cnt=1, max_back_cnt=3, max_fwd_len=200, max_delta_t=None, profile_path=None):

    slices = parse_slices(slices)
    types, messages = read_profile(log, warn=warn, profile_path=profile_path)
    data = bytearray(data)

    log_data('Initial', data)

    if add_header:
        data = prepend_header(data, header_size, protocol_version, profile_version)

    if drop:
        slices = drop_data(State(types, messages, max_delta_t=max_delta_t), data, warn=warn, force=force,
                           min_sync_cnt=min_sync_cnt, max_record_len=max_record_len, max_drop_cnt=max_drop_cnt,
                           max_back_cnt=max_back_cnt, max_fwd_len=max_fwd_len)

    if slices:
        data = apply_slices(data, slices)

    if start:
        data = set_start(data, types, messages, start)

    if fix_header or fix_checksum:
        data = header_and_checksums(data, State(types, messages, max_delta_t=max_delta_t),
                                    fix_header=fix_header, fix_checksum=fix_checksum,
                                    header_size=header_size, protocol_version=protocol_version,
                                    profile_version=profile_version)

    if validate:
        validate_data(data, State(types, messages, max_delta_t=max_delta_t), warn=warn, force=force)

    log_data('Final', data)

    return data


def parse_slices(slices):
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


def log_data(title, data):
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


def prepend_header(data, header_size, protocol_version, profile_version):

    log.info('Add Header ----------')

    header_size = set_default(HEADER_SIZE, header_size, 14)
    protocol_version = set_default(PROTOCOL_VERSION, protocol_version, 0x10)  # from FR35
    profile_version = set_default(PROFILE_VERSION, profile_version, 0x07de)  # from FR35

    data = bytearray([header_size] + [0] * (header_size - 1)) + data
    header = FileHeader(data)
    header.repair(data, log,
                  header_size=header_size, protocol_version=protocol_version, profile_version=profile_version)
    data[:len(header)] = header.data
    return data


def log_param(name, value):
    log.info('%s %s' % (mm(name), value))


def set_default(name, value, deflt):
    if value is None:
        value = deflt
    log_param(name, value)
    return value


def header_and_checksums(data, initial_state, fix_header=False, fix_checksum=False,
                         header_size=None, protocol_version=None, profile_version=None):
    log.info('Header and Checksums ----------')
    log_param(HEADER_SIZE, header_size)
    log_param(PROTOCOL_VERSION, protocol_version)
    log_param(PROFILE_VERSION, profile_version)
    if fix_header:
        data = process_header(data, header_size=header_size, protocol_version=protocol_version,
                              profile_version=profile_version)
    if fix_checksum:
        data = process_checksum(data, initial_state.copy())
    if fix_header and fix_checksum:
        data = process_header(data)  # if length changed with checksum
        data = process_checksum(data, initial_state.copy())  # if length changed
    return data


def process_header(data, header_size=None, protocol_version=None, profile_version=None):
    try:
        with memoryview(data) as view:
            header = FileHeader(view)
            old_size = header.header_size
            # if these are undefined, use existing values (might be used if size changes)
            if protocol_version is None:
                protocol_version = header.protocol_version
            if profile_version is None:
                profile_version = header.profile_version
            prev_len = len(header)
            header.repair(data, log, header_size=header_size, protocol_version=protocol_version, profile_version=profile_version)
            new_data = header.data
        # need to mutate if length changed (in which case header.data is no longer a memoryview)
        if header.header_size != old_size:
            data[:prev_len] = new_data
        return data
    except Exception as e:
        log.error(e)
        raise Exception('Error fixing header - maybe try %s' % mm(ADD_HEADER))


def process_checksum(data, state):
    offset = 0
    try:
        # don't use memoryview here as it gets spread into state and token
        offset = len(FileHeader(data))
        while len(data) - offset > 2:
            token = token_factory(data[offset:], state)
            offset += len(token)
        if len(data) - offset < 2:
            n = offset + 2 - len(data)
            log.warning('Adding %d byte(s) for checksum' % n)
            data += bytearray([0] * n)
        with memoryview(data) as view:
            checksum = Checksum(view[offset:])
            checksum.repair(view, log)
        return data
    except Exception as e:
        log.error(e)
        raise Exception('Error fixing checksum at offset %d' % offset)


def apply_slices(data, slices):

    log.info('Slice ----------')
    log.info('Slices: %s' % format_slices(slices))

    result = bytearray()
    for slice in slices:
        result += data[slice]
    log.info('Have %d bytes after slicing' % len(result))
    dropped = len(data) - len(result)
    if dropped:
        log.warning('Slicing decreased length by %d bytes' % dropped)

    return result


class StartState(State):

    def __init__(self, types, messages, start, max_delta_t=None):
        super().__init__(types, messages, max_delta_t=max_delta_t)
        self.__start = start
        self.__delta = None

    @property
    def timestamp(self):
        return self._timestamp

    @timestamp.setter
    def timestamp(self, timestamp):
        if self.__delta is None:
            self.__delta = self.__start - timestamp
            log.warning('Shifting timestamps by %s' % format_seconds(self.__delta.total_seconds()))
        self._timestamp = self._validate_timestamp(timestamp + self.__delta)


def set_start(data, types, messages, start):

    log.info('Start ----------')
    log.info('Start: %s' % format_time(start))

    state = StartState(types, messages, start)
    with memoryview(data) as view:
        offset = len(FileHeader(view))
        while len(view) - offset > 2:
            token = token_factory(view[offset:], state)
            token.repair_timestamp(state)
            offset += len(token)

    return data


def validate_data(data, state, warn=False, force=True):

    log.info('Validation ----------')
    log_param(MAX_DELTA_T, state.max_delta_t)
    if state.max_delta_t is None:
        log.warning('Time-reversal is allowed unless %s is set' % MAX_DELTA_T)

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
        if state.timestamp > dt.datetime.now(tz=dt.timezone.utc):
            log.warning('Timestamp in future')
        checksum = Checksum(data[offset:])
        checksum.validate(data, log)
        log.info('OK')
    except Exception as e:
        log.error(e)
        log.info('Validation failed')
        raise


def drop_data(initial_state, data, warn=False, force=True,
              min_sync_cnt=3, max_record_len=None, max_drop_cnt=1, max_back_cnt=3, max_fwd_len=200):

    log.info('Drop Data ----------')
    for (name, value) in [(MIN_SYNC_CNT, min_sync_cnt), (MAX_RECORD_LEN, max_record_len),
                          (MAX_DROP_CNT, max_drop_cnt), (MAX_BACK_CNT, max_back_cnt),
                          (MAX_FWD_LEN, max_fwd_len), (MAX_DELTA_T, initial_state.max_delta_t)]:
        log_param(name, value)

    # use memoryview for efficient slicing (although it doesn't seem to help much)
    with memoryview(data) as view:
        slices = advance(initial_state, view,
                         drop_count=0, initial_offset=0, warn=warn, force=force,
                         min_sync_cnt=min_sync_cnt, max_record_len=max_record_len, max_drop_cnt=max_drop_cnt,
                         max_back_cnt=max_back_cnt, max_fwd_len=max_fwd_len)
    log.info('Found slices %s' % format_slices(slices))
    return slices


def offset_tokens(state, data, offset=0, warn=False, force=True):
    '''
    this yields the offsets *after* the tokens (unlike tokens() in the read module).
    '''
    try:
        if not offset:
            file_header = FileHeader(data[offset:])
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
    except Exception as e:
        raise Exception('Error (%s) at offset %d' % (e, offset))


def slurp(state, data, initial_offset, warn=False, force=True, max_record_len=None):
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
        log.debug(e)
        log.debug('Reading from offset %s found %d tokens before %d' %
                  (initial_offset, len(offsets_and_states), offset))
        return offsets_and_states, False


class Backtrack(Exception): pass


def advance(initial_state, data, drop_count=0, initial_offset=0, warn=False, force=True,
            min_sync_cnt=3, max_record_len=None, max_drop_cnt=1, max_back_cnt=3, max_fwd_len=200):
    '''
    try to synchronize on the stream and then read as much as possible.  if reading later fails,
    then try recurse if not at limit; if that fails, backtrack a record and try again.

    finally return the offsets used.

    "synchronize" means progressively discard data until some number of records smaller than
    some length can be read.
    '''
    initial_offsets_and_states = [(initial_offset, initial_state.copy())]
    offsets_and_states, complete = slurp(initial_state, data, initial_offset,
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
                return [slice(initial_offset, offset)]
            else:
                try:
                    log.debug('%d: Retrying (drop %d, skip %d) at offset %d' %
                              (drop_count, back_cnt-1, delta, offset+delta))
                    slices = advance(state.copy(), data, drop_count+1, offset+delta,
                                     min_sync_cnt=min_sync_cnt, max_record_len=max_record_len,
                                     max_drop_cnt=max_drop_cnt, max_fwd_len=max_fwd_len)
                    return [slice(initial_offset, offset)] + slices
                except Backtrack as e:
                    log.debug('%d: Backtrack at (drop %d, skip %d): "%s"' % (drop_count, back_cnt, delta, e))
    raise Backtrack('Search exhausted at %d' % initial_offset)

