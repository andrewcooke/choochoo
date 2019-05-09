
from logging import getLogger

from .args import no, PATH, FORMAT, ALL_FIELDS, ALL_MESSAGES, LIMIT_RECORDS, WARN, GREP, MESSAGE, NAME, NOT, MATCH, \
    WIDTH, VALIDATE, INTERNAL, MAX_DELTA_T, AFTER_BYTES, AFTER_RECORDS, CONTEXT, LIMIT_BYTES, COMPACT, FIELD
from ..fit.profile.profile import read_fit
from ..fit.summary import summarize

log = getLogger(__name__)


def fit(args, db):
    '''
## fit

    > ch2 fit PATH [PATH ...]

Print the contents of fit files.

The format and details displayed can be selected with --records,
--tables, --grep, --messages, --fields, and --csv.

For full options see `ch2 fit -h`.

Note: When using bash use `shopt -s globstar` to enable ** globbing.

### Examples

    > ch2 -v 0 fit --records ride.fit

Will print the contents of the file to stdout (use `-v 0` to suppress logging
or redirect stderr elsewhere).

    > ch2 -v 0 fit --grep '.*:sport=cycling' --match 0 --name directory/**/*.fit

Will list file names that contain cycling data.

    > ch2 fit --grep PATTERN -- FILE

You may need a `--` between patterns and file paths so that the argument parser can decide where patterns
finish and paths start.
    '''
    for file_path in args[PATH]:
        summarize(args[FORMAT], read_fit(log, file_path),
                  all_fields=args[ALL_FIELDS], all_messages=args[ALL_MESSAGES], internal=args[INTERNAL],
                  after_bytes=args[AFTER_BYTES], limit_bytes=args[LIMIT_BYTES],
                  after_records=args[AFTER_RECORDS], limit_records=args[LIMIT_RECORDS],
                  messages=args[MESSAGE], fields=args[FIELD], warn=args[WARN], grep=args[GREP],
                  name_file=file_path if args[NAME] else None, invert=args[NOT], match=args[MATCH],
                  compact=args[COMPACT], context=args[CONTEXT], no_validate=args[no(VALIDATE)],
                  max_delta_t=args[MAX_DELTA_T], width=args[WIDTH])
