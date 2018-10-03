
from .args import PATH, DUMP_FORMAT, ALL_FIELDS, ALL_MESSAGES, AFTER, LIMIT, RECORD, WARN
from ..fit.summary import summarize


def fit(args, log, profile_path=None):
    '''
# fit

    ch2 fit file.fit

Print the contents of a fit file.

The format and details displayed can be selected with --records,
--messages, --fields, and --csv.

For full options see `ch2 dump-fit -h`.

## Example

    ch2 -v 0 dump-fit ride.fit

Will print the contents of the file to stdout (use `-v 0` to suppress logging
or redirect stderr elsewhere).
    '''
    fit_path = args.file(PATH, 0, rooted=False)
    summarize(log, args[DUMP_FORMAT], fit_path, all_fields=args[ALL_FIELDS], all_messages=args[ALL_MESSAGES],
              after=args[AFTER][0], limit=args[LIMIT][0], records=args[RECORD], warn=args[WARN],
              profile_path=profile_path)
