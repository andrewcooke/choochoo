
from collections import Counter, defaultdict
from re import compile
from sys import stdout

from .format.read import filtered_records, filtered_tokens
from .format.records import no_bad_values, fix_degrees, append_units, no_unknown_fields, unique_names, join_values, \
    to_hex, no_filter
from ..command.args import RECORDS, FIELDS, CSV, TABLES, GREP, TOKENS
from ..lib.io import terminal_width
from ..lib.utils import unique


def summarize(log, format, data, all_fields=False, all_messages=False, after=0, limit=-1,
              messages=None, warn=False, profile_path=None, grep=None, name_file=None, invert=False, match=1,
              no_header=False, width=None, output=stdout):
    if name_file and format != GREP:
        print()
        print(name_file)
    if format == RECORDS:
        summarize_records(log, data,
                          all_fields=all_fields, all_messages=all_messages,
                          after=after, limit=limit, messages=messages, warn=warn, no_header=no_header,
                          profile_path=profile_path, width=width, output=output)
    elif format == TABLES:
        summarize_tables(log, data,
                         all_fields=all_fields, all_messages=all_messages,
                         after=after, limit=limit, messages=messages, warn=warn, no_header=no_header,
                         profile_path=profile_path, width=width, output=output)
    elif format == GREP:
        summarize_grep(log, data, grep, name_file=name_file, match=match, invert=invert,
                       after=after, limit=limit, warn=warn, no_header=no_header,
                       profile_path=profile_path, output=output)
    elif format == CSV:
        summarize_csv(log, data,
                      after=after, limit=limit, warn=warn, no_header=no_header,
                      profile_path=profile_path, output=output)
    elif format == TOKENS:
        summarize_tokens(log, data,
                         after=after, limit=limit, warn=warn, no_header=no_header,
                         profile_path=profile_path, output=output)
    elif format == FIELDS:
        summarize_fields(log, data,
                         after=after, limit=limit, warn=warn, no_header=no_header,
                         profile_path=profile_path, output=output)
    else:
        raise Exception('Bad format: %s' % format)


def summarize_tokens(log, data, after=0, limit=-1, warn=False, no_header=False,
                     profile_path=None, output=stdout):
    types, messages, tokens = \
        filtered_tokens(log, data, after=after, limit=limit, warn=warn, no_header=no_header,
                        profile_path=profile_path)
    for index, offset, token in tokens:
        print('%03d %05d %s' % (index, offset, token), file=output)


def summarize_fields(log, data, after=0, limit=-1, warn=False, no_header=False,
                     profile_path=None, output=stdout):
    types, messages, tokens = \
        filtered_tokens(log, data, after=after, limit=limit, warn=warn, no_header=no_header,
                        profile_path=profile_path)
    for index, offset, token in tokens:
        print('%03d %05d %s' % (index, offset, token), file=output)
        for line in token.describe_fields(types):
            print('  %s' % line, file=output)


def summarize_records(log, data, all_fields=False, all_messages=False, after=0, limit=-1, messages=None,
                      warn=False, no_header=False, profile_path=None, width=None, output=stdout):
    types, messages, records = \
        filtered_records(log, data, after=after, limit=limit, record_names=messages, warn=warn,
                         no_header=no_header, profile_path=profile_path)
    records = list(records)
    width = width or terminal_width()
    print(file=output)
    pprint_as_dicts(records, all_fields, all_messages, width=width, output=output)


def summarize_tables(log, data, all_fields=False, all_messages=False, after=0, limit=-1, messages=None,
                     warn=False, no_header=False, profile_path=None, width=None, output=stdout):
    types, messages, records = \
        filtered_records(log, data, after=after, limit=limit, record_names=messages, warn=warn,
                         no_header=no_header, profile_path=profile_path)
    records = list(records)
    counts = Counter(record.identity for record in records)
    small, large = partition(records, counts)
    width = width or terminal_width()
    print(file=output)
    pprint_as_dicts(small, all_fields, all_messages, width=width, output=output)
    pprint_as_tuples(large, all_fields, all_messages, width=width, output=output)


class Done(Exception):
    pass


def summarize_grep(log, fit_path, data, grep, name_file=None, match=1, invert=False, after=0, limit=-1,
                   warn=False, no_header=False, profile_path=None, output=stdout):
    types, messages, records = \
        filtered_records(log, data, warn=warn, no_header=no_header, profile_path=profile_path)
    matchers = [compile(pattern) for pattern in grep]
    counts = defaultdict(lambda: 0)
    first = True
    try:
        for n, record in enumerate(records):
            if n >= after:
                if n < after + limit or limit < 0:
                    record = record.as_dict(join_values, append_units, to_hex, fix_degrees, no_bad_values)
                    for name, value in sorted(record.data.items()):
                        target_1 = '%s:%s' % (record.name, name)
                        target_2 = '%s:%s=%s' % (record.name, name, value)
                        for matcher in matchers:
                            if matcher.match(target_2 if '=' in matcher.pattern else target_1):
                                counts[matcher] += 1
                                if counts[matcher] <= match or match < 0:
                                    if first:
                                        print(file=output)
                                        first = False
                                    print('%s:%s=%s' % (record.name, name, value), file=output)
                                # exit early if we've displayed/matched all we need to
                                if match > -1 and all(counts[m] >= max(1, match) for m in matchers):
                                    raise Done()
                else:
                    raise Done()
    except Done:
        pass
    if name_file:
        if (not all(counts[m] for m in matchers)) == invert:
            print(name_file, file=output)


def summarize_csv(log, data, after=0, limit=-1, warn=False, no_header=False, profile_path=None,
                  output=stdout):
    types, messages, tokens = \
        filtered_tokens(log, data, after=after, limit=limit, warn=warn, no_header=no_header,
                        profile_path=profile_path)
    for index, offset, token in tokens:
        if hasattr(token, 'describe_csv'):
            print(','.join(str(component) for component in token.describe_csv()), file=output)


def partition(records, counts, threshold=3):
    small, large = [], []
    for record in records:
        if counts[record.identity] <= threshold:
            small.append(record)
        else:
            large.append(record)
    return small, large


def pprint_as_dicts(records, all_fields, all_messages, width=80, output=stdout):
    for record in records:
        if all_messages or record.is_known():
            record = record.as_dict(join_values, append_units, to_hex, fix_degrees,
                                    no_filter if all_fields else no_unknown_fields,
                                    no_bad_values)
            print(record.identity, file=output)
            pprint_with_tabs(('%s: %s' % (name, value) for name, value in sorted(record.data.items())),
                             width=width, output=output)
            print(file=output)


def sort_names(data):
    return sorted(list(data), key=lambda x: ' ' if x[0] == 'timestamp' else x[0])


def pprint_as_tuples(records, all_fields, all_messages, width=80, output=stdout):
    records = [record.force(sort_names, unique_names,
                            timestamp=([record.timestamp], 's'))
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
                      width=width, output=output)


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


def pprint_series(title, records, width=80, output=stdout):
    print(title.identity, file=output)
    lengths = measure_lengths([title], keep_bad=True, lengths=measure_lengths(records))
    pprint_with_tabs(pad_to_lengths(title, lengths), first_indent=2, indent=4, separator='',
                     width=width, output=output)
    for record in records:
        pprint_with_tabs(pad_to_lengths(record, lengths), first_indent=2, indent=4, separator='',
                         width=width, output=output)
    print(file=output)


def pprint_with_tabs(data, first_indent=None, indent=2, tab=4, width=80, min_space=2, separator=',', output=stdout):
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
                print(line, file=output)
                line = ' ' * indent + datum
            else:
                line += ' ' * (l_new - l_old) + datum
        else:
            line += datum
        first = False
    if len(line) > indent:
        print(line, file=output)
