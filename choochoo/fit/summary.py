
from collections import Counter

from .format.records import no_bad_values, fix_degrees, append_units, no_unknown_fields, unique_names, join_values, \
    to_hex, no_filter
from .format.tokens import filtered_records, filtered_tokens
from .profile.types import Date
from ..args import PATH, ALL_FIELDS, ALL_MESSAGES, AFTER, LIMIT, DUMP_FORMAT, MESSAGES, RECORDS, FIELDS
from ..lib.data import tohex
from ..lib.io import terminal_width
from ..utils import unique


def dump_fit(args, log, profile_path=None):
    '''
# dump-fit

    ch2 dump-fit FILE.FIT

Print the contents of a fit file.

For full options see `ch2 dump-fit -h`.

## Example

    ch2 -v 0 dump-fit ride.fit

Will print the contents of the file to stdout (use `-v 0` to suppress logging
or redirect stderr elsewhere).
    '''
    fit_path = args.file(PATH, 0, rooted=False)
    summarize(log, args[DUMP_FORMAT], fit_path, all_fields=args[ALL_FIELDS], all_messages=args[ALL_MESSAGES],
              after=args[AFTER][0], limit=args[LIMIT][0], profile_path=profile_path)


def summarize(log, format, fit_path, all_fields=False, all_messages=False, after=0, limit=-1, profile_path=None):
    if format == MESSAGES:
        summarize_messages(log, fit_path,
                           after=after, limit=limit, profile_path=profile_path)
    elif format == FIELDS:
        summarize_fields(log, fit_path,
                         after=after, limit=limit, profile_path=profile_path)
    elif format == RECORDS:
        summarize_records(log, fit_path,
                          all_fields=all_fields, all_messages=all_messages,
                          after=after, limit=limit, profile_path=profile_path)
    else:
        raise Exception('Bad format: %s' % format)


def summarize_messages(log, fit_path, after=0, limit=-1, profile_path=None):
    for index, offset, token in filtered_tokens(log, fit_path, after=after, limit=limit, profile_path=profile_path):
        print('%03d %05d %s' % (index, offset, token))


def summarize_fields(log, fit_path, after=0, limit=-1, profile_path=None):
    tokens = filtered_tokens(log, fit_path, after=after, limit=limit, profile_path=profile_path, include_data=True)
    data, types = next(tokens)
    for index, offset, token in filtered_tokens(log, fit_path, after=after, limit=limit, profile_path=profile_path):
        print('%03d %05d %s' % (index, offset, token))
        for line in token.describe(types):
            print('  %s' % line)


def summarize_records(log, fit_path, all_fields=False, all_messages=False, after=0, limit=-1, profile_path=None):
    records = list(filtered_records(log, fit_path, after=after, limit=limit, profile_path=profile_path))
    counts = Counter(record.identity for record in records)
    small, large = partition(records, counts)
    width = terminal_width()
    print()
    pprint_as_dicts(small, all_fields, all_messages, width=width)
    pprint_as_tuples(large, all_fields, all_messages, width=width)


def partition(records, counts, threshold=3):
    small, large = [], []
    for record in records:
        if counts[record.identity] <= threshold:
            small.append(record)
        else:
            large.append(record)
    return small, large


def pprint_as_dicts(records, all_fields, all_messages, width=80):
    for record in records:
        if all_messages or record.is_known():
            record = record.as_dict(join_values, append_units, to_hex, fix_degrees,
                                    no_filter if all_fields else no_unknown_fields,
                                    no_bad_values)
            print(record.identity)
            pprint_with_tabs(('%s: %s' % (name, value) for name, value in sorted(record.data.items())),
                             width=width)
            print()


def sort_names(data):
    return sorted(list(data), key=lambda x: ' ' if x[0] == 'timestamp' else x[0])


def pprint_as_tuples(records, all_fields, all_messages, width=80):
    records = [record.force(sort_names, unique_names,
                            timestamp=([Date.convert(record.timestamp)], 's'))
               for record in records]
    titles = [record.as_names(no_filter if all_fields else no_unknown_fields)
              for record in unique(records, key=lambda x: x.identity)
              if all_messages or record.is_known()]
    for title in titles:
        pprint_series(title,
                      [record.as_values(join_values, append_units, to_hex, fix_degrees,
                                        no_filter if all_fields else no_unknown_fields)
                       for record in records
                       if record.identity == title.identity],
                      width=width)


def measure_lengths(records, lengths=None, separator=',', keep_bad=False):
    for record in records:
        if lengths is None:
            lengths = [(len(datum) + (len(separator) if i+1 < len(record.data) else 0)) if datum else 0
                       for i, datum in enumerate(record.data)]
        else:
            for i, datum in enumerate(record.data):
                if datum and (lengths[i] or not keep_bad):
                    lengths[i] = max(lengths[i], len(datum) + (len(separator) if i+1 < len(record.data) else 0))
    return lengths


def pad_to_lengths(record, lengths, separator=',', bad='-'):
    for i, datum in enumerate(record.data):
        if lengths[i]:
            if datum:
                yield (datum + (separator if i+1 < len(lengths) else '')).ljust(lengths[i])
            else:
                yield bad.ljust(lengths[i])


def pprint_series(title, records, width=80):
    print(title.identity)
    lengths = measure_lengths([title], keep_bad=True, lengths=measure_lengths(records))
    pprint_with_tabs(pad_to_lengths(title, lengths), first_indent=2, indent=4, separator='', width=width)
    for record in records:
        pprint_with_tabs(pad_to_lengths(record, lengths), first_indent=2, indent=4, separator='', width=width)
    print()


def pprint_with_tabs(data, first_indent=None, indent=2, tab=4, width=80, min_space=2, separator=','):
    if first_indent is None:
        first_indent = indent
    min_space -= 1
    line = ' ' * first_indent
    first = True
    for datum in data:
        if not first:
            line += separator
        l_old = len(line)
        if l_old > indent:
            l_new = (1 + (l_old - indent + min_space) // tab) * tab + indent
            # equality here leaves an attractive space at end of line
            if l_new + len(datum) >= width:
                print(line)
                line = ' ' * indent + datum
            else:
                line += ' ' * (l_new - l_old) + datum
        else:
            line += datum
        first = False
    if len(line) > indent:
        print(line)
