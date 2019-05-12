
from logging import getLogger

from ch2.fit.profile.profile import read_fit
from ch2.fit.summary import summarize_records, summarize_tables, summarize_grep, summarize_csv, summarize_tokens, \
    summarize_fields
from ch2.lib.io import terminal_width
from .args import PATH, SUB_COMMAND, AFTER_BYTES, LIMIT_BYTES, AFTER_RECORDS, LIMIT_RECORDS, NAME, WIDTH, GREP, \
    RECORDS, ALL_FIELDS, INTERNAL, ALL_MESSAGES, MESSAGE, FIELD, VALIDATE, MAX_DELTA_T, no, WARN, TABLES, PATTERN, \
    COMPACT, CONTEXT, NOT, MATCH, CSV, TOKENS, FIELDS

log = getLogger(__name__)


def fit(args, db):
    '''
## fit

    > ch2 fit SUB-COMMAND PATH [PATH ...]

Print the contents of fit files.

The format and details displayed is selected by the sub-command: records, tables, messages, fields, csv
and grep (the last requiring patterns to match against).

For a list of sub-commands options see `ch2 fit -h`.

For options for a particular sub-command see `ch2 fit sub-command -h`.

Note: When using bash use `shopt -s globstar` to enable ** globbing.

### Examples

    > ch2 -v 0 fit records ride.fit

Will print the contents of the file to stdout (use `-v 0` to suppress logging
or redirect stderr elsewhere).

    > ch2 -v 0 fit grep -p '.*:sport=cycling' --match 0 --name directory/**/*.fit

Will list file names that contain cycling data.

    > ch2 fit grep -p PATTERN -- FILE

You may need a `--` between patterns and file paths so that the argument parser can decide where patterns
finish and paths start.
    '''

    format = args[SUB_COMMAND]
    after_bytes = args[AFTER_BYTES]
    limit_bytes = args[LIMIT_BYTES]
    after_records = args[AFTER_RECORDS]
    limit_records = args[LIMIT_RECORDS]
    warn = args[WARN]
    no_validate = args[no(VALIDATE)]
    max_delta_t = args[MAX_DELTA_T]

    # todo - can this be handled by argparse?
    if (after_records or limit_records != -1) and (after_bytes or limit_bytes != -1):
        raise Exception('Constrain either records or bytes, not both')

    for file_path in args[PATH]:

        name_file = file_path if args[NAME] else None
        if name_file and format != GREP:
            print()
            print(name_file)

        data = read_fit(log, file_path)

        if format == RECORDS:
            summarize_records(data,
                              all_fields=args[ALL_FIELDS], all_messages=args[ALL_MESSAGES],
                              internal=args[INTERNAL], after_bytes=after_bytes, limit_bytes=limit_bytes,
                              after_records=after_records, limit_records=limit_records,
                              record_names=args[MESSAGE], field_names=args[FIELD],
                              warn=warn, no_validate=no_validate, max_delta_t=max_delta_t,
                              width=args[WIDTH] or terminal_width())
        elif format == TABLES:
            summarize_tables(data,
                             all_fields=args[ALL_FIELDS], all_messages=args[ALL_MESSAGES],
                             internal=args[INTERNAL], after_bytes=after_bytes, limit_bytes=limit_bytes,
                             after_records=after_records, limit_records=limit_records,
                             record_names=args[MESSAGE], field_names=args[FIELD],
                             warn=warn, no_validate=no_validate, max_delta_t=max_delta_t,
                             width=args[WIDTH] or terminal_width())
        elif format == CSV:
            summarize_csv(data,
                          internal=args[INTERNAL], after_bytes=after_bytes, limit_bytes=limit_bytes,
                          after_records=after_records, limit_records=limit_records,
                          record_names=args[MESSAGE], field_names=args[FIELD],
                          warn=warn, max_delta_t=max_delta_t)
        elif format == GREP:
            summarize_grep(data, args[PATTERN],
                           after_bytes=after_bytes, limit_bytes=limit_bytes,
                           after_records=after_records, limit_records=limit_records,
                           warn=warn, no_validate=no_validate, max_delta_t=max_delta_t,
                           width=args[WIDTH] or terminal_width(),
                           name_file=name_file, match=args[MATCH], compact=args[COMPACT],
                           context=args[CONTEXT], invert=args[NOT])
        elif format == TOKENS:
            summarize_tokens(data,
                             after_bytes=after_bytes, limit_bytes=limit_bytes,
                             after_records=after_records, limit_records=limit_records,
                             warn=warn, no_validate=no_validate, max_delta_t=max_delta_t)
        elif format == FIELDS:
            summarize_fields(data,
                             after_bytes=after_bytes, limit_bytes=limit_bytes,
                             after_records=after_records, limit_records=limit_records,
                             warn=warn, no_validate=no_validate, max_delta_t=max_delta_t)
        else:
            raise Exception('Bad format: %s' % format)
