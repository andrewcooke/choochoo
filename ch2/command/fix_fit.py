
from .args import PATH, DROP, OUTPUT, SLICES, mm, RAW, WARN, MIN_SYNC_CNT, MAX_RECORD_LEN, MAX_DROP_CNT, MAX_BACK_CNT, \
    MAX_FWD_LEN
from ..fit.fix import fix


def fix_fit(args, log, db):
    '''
## fix-fit

    > ch2 fix-fit PATH -o PATH --drop

Try to fix a corrupted fit file.

By default, the length and checksum are updated.

If `--drop` is specified then the program tries to omit data from the stream until
all the remaining data can be parsed.

### Examples

    > ch2 fix-fit data/tests/personal/8CS90646.FIT --drop -o /dev/null

Will attempt to fix the given file (in the test data from git).
    '''
    fix(log, args[PATH], args[OUTPUT], raw=args[RAW], drop=args[DROP], slices=parse_slices(args[SLICES]),
        warn=args[WARN], min_sync_cnt=args[MIN_SYNC_CNT], max_record_len=args[MAX_RECORD_LEN],
        max_drop_cnt=args[MAX_DROP_CNT], max_back_cnt=args[MAX_BACK_CNT], max_fwd_len=args[MAX_FWD_LEN])


def parse_slices(slices):
    if not slices:
        return None
    return [parse_slice(slice) for slice in slices.split(',')]


def parse_slice(slice):
    start, stop = (parse_offset(offset) for offset in slice.split(':'))
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
