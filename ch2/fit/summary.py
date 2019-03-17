
from collections import Counter
from logging import getLogger
from operator import eq, lt, gt
from re import compile
from sys import stdout

from .format.read import filtered_records, filtered_tokens
from .format.records import no_bad_values, fix_degrees, append_units, no_unknown_fields, join_values, \
    to_hex, no_filter, merge_duplicates
from ..commands.args import RECORDS, FIELDS, CSV, TABLES, GREP, TOKENS
from ..lib.io import terminal_width
from ..lib.utils import unique

log = getLogger(__name__)


def summarize(format, data, all_fields=False, all_messages=False, internal=False,
              after_bytes=None, limit_bytes=-1, after_records=None, limit_records=-1,
              messages=None, fields=None, warn=False, profile_path=None, grep=None,
              name_file=None, invert=False, match=1, compact=False, context=False, no_validate=False, max_delta_t=None,
              width=None, output=stdout):

    width = width or terminal_width()

    if (after_records or limit_records != -1) and (after_bytes or limit_bytes != -1):
        raise Exception('Constrain either records or bytes, not both')

    if name_file and format != GREP:
        print()
        print(name_file)

    if format == RECORDS:
        summarize_records(data,
                          all_fields=all_fields, all_messages=all_messages, internal=internal,
                          after_bytes=after_bytes, limit_bytes=limit_bytes,
                          after_records=after_records, limit_records=limit_records,
                          record_names=messages, field_names=fields,
                          warn=warn, no_validate=no_validate, max_delta_t=max_delta_t,
                          profile_path=profile_path, width=width, output=output)
    elif format == TABLES:
        summarize_tables(data,
                         all_fields=all_fields, all_messages=all_messages, internal=internal,
                         after_bytes=after_bytes, limit_bytes=limit_bytes,
                         after_records=after_records, limit_records=limit_records,
                         record_names=messages, field_names=fields,
                         warn=warn, no_validate=no_validate, max_delta_t=max_delta_t,
                         profile_path=profile_path, width=width, output=output)
    elif format == GREP:
        summarize_grep(data, grep,
                       name_file=name_file, match=match, compact=compact, context=context, invert=invert,
                       after_bytes=after_bytes, limit_bytes=limit_bytes,
                       after_records=after_records, limit_records=limit_records,
                       warn=warn, no_validate=no_validate, max_delta_t=max_delta_t, profile_path=profile_path,
                       width=width, output=output)
    elif format == CSV:
        summarize_csv(data,
                      after_bytes=after_bytes, limit_bytes=limit_bytes, internal=internal,
                      after_records=after_records, limit_records=limit_records,
                      record_names=messages, field_names=fields, warn=warn, no_header=no_validate,
                      max_delta_t=max_delta_t, profile_path=profile_path,
                      output=output)
    elif format == TOKENS:
        summarize_tokens(data,
                         after_bytes=after_bytes, limit_bytes=limit_bytes,
                         after_records=after_records, limit_records=limit_records,
                         warn=warn, no_validate=no_validate, max_delta_t=max_delta_t, profile_path=profile_path,
                         output=output)
    elif format == FIELDS:
        summarize_fields(data,
                         after_bytes=after_bytes, limit_bytes=limit_bytes,
                         after_records=after_records, limit_records=limit_records,
                         warn=warn, no_validate=no_validate, max_delta_t=max_delta_t, profile_path=profile_path,
                         output=output)
    else:
        raise Exception('Bad format: %s' % format)


def summarize_tokens(data, after_bytes=None, limit_bytes=-1, after_records=None, limit_records=-1,
                     warn=False, no_validate=False, max_delta_t=None, profile_path=None, output=stdout):

    types, messages, tokens = \
        filtered_tokens(data,
                        after_bytes=after_bytes, limit_bytes=limit_bytes,
                        after_records=after_records, limit_records=limit_records,
                        warn=warn, no_validate=no_validate, max_delta_t=max_delta_t, profile_path=profile_path)

    for index, offset, token in tokens:
        print('%03d %05d %s' % (index, offset, token), file=output)


def summarize_fields(data, after_bytes=None, limit_bytes=-1, after_records=None, limit_records=-1,
                     warn=False, no_validate=False, max_delta_t=None, profile_path=None, output=stdout):

    types, messages, tokens = \
        filtered_tokens(data,
                        after_bytes=after_bytes, limit_bytes=limit_bytes,
                        after_records=after_records, limit_records=limit_records,
                        warn=warn, no_validate=no_validate, max_delta_t=max_delta_t, profile_path=profile_path)

    for index, offset, token in tokens:
        print('%03d %05d %s' % (index, offset, token), file=output)
        for line in token.describe_fields(types):
            print('  %s' % line, file=output)


def summarize_records(data, all_fields=False, all_messages=False, internal=False,
                      after_bytes=None, limit_bytes=-1, after_records=None, limit_records=-1,
                      record_names=None, field_names=None,
                      warn=False, no_validate=False, max_delta_t=None, profile_path=None,
                      width=None, output=stdout):

    types, messages, records = \
        filtered_records(data,
                         after_bytes=after_bytes, limit_bytes=limit_bytes,
                         after_records=after_records, limit_records=limit_records,
                         record_names=record_names, field_names=field_names,
                         warn=warn, no_validate=no_validate, internal=internal,
                         profile_path=profile_path, max_delta_t=max_delta_t, pipeline=[merge_duplicates])

    records = list(records)
    print(file=output)
    pprint_as_dicts(records, all_fields, all_messages, width=width, output=output)


def summarize_tables(data, all_fields=False, all_messages=False, internal=False,
                     after_bytes=None, limit_bytes=-1, after_records=None, limit_records=-1,
                     record_names=None, field_names=None,
                     warn=False, no_validate=False, max_delta_t=None, profile_path=None,
                     width=None, output=stdout):

    types, messages, records = \
        filtered_records(data,
                         after_bytes=after_bytes, limit_bytes=limit_bytes,
                         after_records=after_records, limit_records=limit_records,
                         record_names=record_names, field_names=field_names,
                         warn=warn, no_validate=no_validate, internal=internal,
                         profile_path=profile_path, max_delta_t=max_delta_t, pipeline=[merge_duplicates])

    records = list(record[2] for record in records)
    counts = Counter(record.identity for record in records)
    small, large = partition(records, counts)
    width = width or terminal_width()
    print(file=output)
    pprint_as_dicts(small, all_fields, all_messages, width=width, output=output, full_name=False)
    pprint_as_tuples(large, all_fields, all_messages, width=width, output=output)


class Done(Exception): pass


CMP = compile(r'([^=<>~]+)([=<>~])([^=<>~]+)')


class Matcher:

    def __init__(self, log, pattern):
        if ':' in pattern:
            record, pattern = pattern.split(':', 1)
            self.record = compile(record).match
        else:
            self.record = None
        match = CMP.match(pattern)
        if match:
            self.field = compile(match.group(1)).match
            if match.group(2) == '~':
                self.value = compile(match.group(2)).match
            else:
                try:
                    try:
                        value = float(match.group(3))
                        log.debug('Matching %f as a float' % value)
                    except ValueError:
                        value = match.group(3)
                        log.debug('Matching %s as a string' % value)
                    self.value = {'=': self.__build_compare(eq, value),
                                  '<': self.__build_compare(lt, value),
                                  '>': self.__build_compare(gt, value)}[match.group(2)]
                except:
                    if match.group(2) != '=':
                        raise Exception('Comparison "%s" with non-numerical value "%s"' %
                                        (match.group(2), match.group(3)))
                    self.value = lambda v: v == match.group(3)
                    print('STRING', self.value)
        else:
            self.field = compile(pattern).match
            self.value = None

    def __build_compare(self, op, value):
        def compare(v):
            if isinstance(value, float):
                try:
                    v = float(v)
                    return op(v, value)
                except:
                    return False
            else:
                return op(str(v), value)
        return compare

    def match(self, record, field, value):
        return (self.record is None or self.record(record)) and \
               (self.field is None or self.field(field)) and \
               (self.value is None or self.value(value))


def summarize_grep(data, grep, name_file=None, match=1, compact=False, context=False, invert=False,
                   after_bytes=None, limit_bytes=-1, after_records=None, limit_records=-1,
                   warn=False, no_validate=False, max_delta_t=None, profile_path=None, width=80, output=stdout):

    types, messages, records = \
        filtered_records(data, warn=warn, no_validate=no_validate, profile_path=profile_path,
                         max_delta_t=max_delta_t, pipeline=[merge_duplicates])
    matchers = [Matcher(log, pattern) for pattern in grep]
    first, total_matches = True, 0
    first_record = 0 if (after_records is None) else None
    first_bytes = 0 if (after_bytes is None) else None

    try:
        for index, offset, record in records:
            matched_matchers, matched_names_values, display = set(), set(), ''
            if (first_record is None and (after_records is not None and index >= after_records)) or \
                    (first_bytes is None and (after_bytes is not None and offset >= after_bytes)):
                first_record, first_bytes = index, offset
            if first_record is not None or first_bytes is not None:
                if (first_record is not None and (limit_records < 0 or i - first_record < limit_records)) and \
                        (first_bytes is not None and (limit_bytes < 0 or offset - first_bytes < limit_bytes)):
                    record = record.as_dict(fix_degrees, merge_duplicates)
                    for name, values_units in sorted(record.data.items()):
                        if values_units and values_units[0]:
                            for value in values_units[0]:
                                for matcher in matchers:
                                    if matcher.match(record.name, name, value):
                                        matched_matchers.add(matcher)
                                        if (name, value) not in matched_names_values:
                                            display += '%s:%s=%s\n' % (record.name, name, value)
                                            matched_names_values.add((name, value))
                    if len(matched_matchers) == len(matchers):
                        total_matches += 1
                        if match:
                            if first:
                                if context or not compact:
                                    print(file=output)
                                first = False
                            if context:
                                pprint_as_dicts([(index, offset, record)], True, True,
                                                width=width, output=output)
                            else:
                                print(display, file=output, end='' if compact else '\n')
                        if match > -1 and total_matches > max(1, match):
                            raise Done()
                else:
                    raise Done()
    except Done:
        pass
    if name_file:
        if not total_matches == invert:
            print(name_file, file=output)


def summarize_csv(data, after_bytes=0, limit_bytes=-1, after_records=0, limit_records=-1, internal=False,
                  record_names=None, field_names=None, warn=False, no_header=False, max_delta_t=None,
                  profile_path=None, output=stdout):
    types, messages, tokens = \
        filtered_tokens(data,
                        after_bytes=after_bytes, limit_bytes=limit_bytes,
                        after_records=after_records, limit_records=limit_records,
                        warn=warn, no_validate=no_header, max_delta_t=max_delta_t, profile_path=profile_path)
    for index, offset, token in tokens:
        if hasattr(token, 'describe_csv'):
            values = ','.join(str(component)
                              for component in token.describe_csv(warn=warn, internal=internal,
                                                                  record_names=record_names, field_names=field_names))
            if values:
                print(values, file=output)


def partition(records, counts, threshold=3):
    small, large = [], []
    for record in records:
        if counts[record.identity] <= threshold:
            small.append(record)
        else:
            large.append(record)
    return small, large


def pprint_as_dicts(records, all_fields, all_messages, width=80, output=stdout, full_name=True):
    for record in records:
        if full_name:
            index, offset, record = record
        if all_messages or record.is_known():
            record = record.as_dict(join_values, append_units, to_hex, fix_degrees,
                                    no_filter if all_fields else no_unknown_fields,
                                    no_bad_values)
            if full_name:
                print('%03d %05d %s' % (index, offset, record.identity), file=output)
            else:
                print(record.name, file=output)
            pprint_with_tabs(('%s: %s' % (name, value) for name, value in sorted(record.data.items())),
                             width=width, output=output)
            print(file=output)


def sort_names(data):
    return sorted(list(data), key=lambda x: ' ' if x[0] == 'timestamp' else x[0])


def pprint_as_tuples(records, all_fields, all_messages, width=80, output=stdout):
    records = [record.as_dict(sort_names, timestamp=((record.timestamp,), 's'))
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
