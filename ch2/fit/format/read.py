
from ..profile.profile import load_fit
from .tokens import State, FileHeader, token_factory, Checksum


def tokens(log, data, types, messages, no_header=False, restart=False):
    state = State(log, types, messages)
    file_header = FileHeader(data)
    yield 0, file_header
    offset = len(file_header)
    file_header.validate(data, log, quiet=no_header)
    while len(data) - offset > 2:
        try:
            token = token_factory(data[offset:], state)
            yield offset, token
            offset += len(token)
        except Exception as e:
            if not restart:
                raise
            else:
                log.warn('Restarting after "%s"' % e)
                restarting, old_offset, timestamp = True, offset, state.timestamp
                while restarting and len(data) - offset > 2:
                    offset += 1
                    state.timestamp = timestamp
                    try:
                        token_factory(data[offset:], state)
                        restarting = False
                        state.timestamp = timestamp
                        log.warn('Restarted at %d (was %d)' % (offset, old_offset))
                    except:
                        pass
                if restarting:
                    raise Exception('Failed to restart')
    checksum = Checksum(data)
    yield offset, checksum
    checksum.validate(offset, log, quiet=no_header)


def filtered_tokens(log, fit_path, after=0, limit=-1, warn=False, no_header=False, restart=False, profile_path=None):
    data, types, messages = load_fit(log, fit_path, warn=warn, profile_path=profile_path)

    def generator():
        for i, (offset, token) in enumerate(tokens(log, data, types, messages, no_header=no_header, restart=restart)):
            if i >= after and (limit < 0 or i - after < limit):
                yield i, offset, token

    return data, types, messages, generator()


def filtered_records(log, fit_path, after=0, limit=-1, records=None, warn=False, no_header=False, restart=False,
                     profile_path=None):
    data, types, messages = load_fit(log, fit_path, warn=warn, profile_path=profile_path)

    def generator():
        for i, (offset, token) in enumerate((offset, token)
                                            for (offset, token) in tokens(log, data, types, messages,
                                                                          no_header=no_header, restart=restart)
                                            if token.is_user):
            if i >= after and (limit < 0 or i - after < limit):
                record = token.parse(warn=warn)
                if not records or record.name in records:
                    yield record

    return data, types, messages, generator()
