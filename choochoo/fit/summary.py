
from collections import Counter

from .decode import parse_all
from .profile import Date
from .records import no_bad_values, fix_degrees, append_units, no_unknown_messages, unique_names, join_values
from ..args import PATH
from ..log import make_log
from ..utils import unique


def dump_fit(args, profile_path=None):
    # todo - remove!
    profile_path='/home/andrew/Downloads/FitSDKRelease_20.67.00/Profile.xlsx'
    log = make_log(args)
    fit_path = args.file(PATH, 0)
    summarize(log, fit_path, profile_path=profile_path)


def summarize(log, fit_path, profile_path=None):
    records = list(parse_all(log, fit_path, profile_path=profile_path))
    counts = Counter(record.identity for record in records)
    small, large = partition(records, counts)
    print()
    pprint_as_dicts(small)
    pprint_as_tuples(large)


def partition(records, counts, threshold=3):
    small, large = [], []
    for record in records:
        if counts[record.identity] <= threshold:
            small.append(record)
        else:
            large.append(record)
    return small, large


def pprint_as_dicts(records):
    for record in records:
        if record.is_known():
            record = record.as_dict(join_values, append_units, fix_degrees, no_unknown_messages, no_bad_values)
            print(record.name)
            pprint_with_tabs('%s: %s' % (name, value) for name, value in sorted(record.data.items()))
            print()


def sort_names(data):
    return sorted(list(data), key=lambda x: ' ' if x[0] == 'timestamp' else x[0])


def pprint_as_tuples(records):
    records = [record.force(sort_names, unique_names,
                            timestamp=([Date.convert(record.timestamp)], 's'))
               for record in records]
    titles = [record.as_names(no_unknown_messages)
              for record in unique(records, key=lambda x: x.identity)
              if record.is_known()]
    for title in titles:
        pprint_series(title, [record.as_values(join_values, append_units, fix_degrees, no_unknown_messages)
                              for record in records
                              if record.identity == title.identity])


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


def pprint_series(title, records):
    print(title.identity)
    lengths = measure_lengths([title], keep_bad=True, lengths=measure_lengths(records))
    pprint_with_tabs(pad_to_lengths(title, lengths), first_indent=2, indent=4, separator='')
    for record in records:
        pprint_with_tabs(pad_to_lengths(record, lengths), first_indent=2, indent=4, separator='')
    print()


def pprint_with_tabs(data, first_indent=None, indent=2, tab=4, width=79, min_space=2, separator=','):
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
            if l_new + len(datum) > width:
                print(line)
                line = ' ' * indent + datum
            else:
                line += ' ' * (l_new - l_old) + datum
        else:
            line += datum
        first = False
    if len(line) > indent:
        print(line)
