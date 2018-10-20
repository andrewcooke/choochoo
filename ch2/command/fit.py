from .args import PATH, FORMAT, ALL_FIELDS, ALL_MESSAGES, AFTER, LIMIT, WARN, GREP, MESSAGE, NAME, NOT, MATCH
from ..fit.summary import summarize


def fit(args, log, db):
    '''
# fit

    ch2 fit PATH [PATH ...]

Print the contents of fit files.

The format and details displayed can be selected with --records,
--tables, --messages, --fields, and --csv.

For full options see `ch2 fit -h`.

## Example

    ch2 -v 0 dump-fit ride.fit

Will print the contents of the file to stdout (use `-v 0` to suppress logging
or redirect stderr elsewhere).
    '''
    for file_path in args[PATH]:
        # there's a change of nomenclature here from message to record that is too much trouble to fix
        summarize(log, args[FORMAT], file_path, all_fields=args[ALL_FIELDS], all_messages=args[ALL_MESSAGES],
                  after=args[AFTER], limit=args[LIMIT], records=args[MESSAGE], warn=args[WARN],
                  grep=args[GREP], name=args[NAME], invert=args[NOT], match=args[MATCH])
