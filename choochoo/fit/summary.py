
from collections import Counter

from .decode import parse_all
from .profile import chain, no_nulls, fix_degrees, append_units, no_unknown
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
    counts = Counter(record.name for record in records)
    small, large = partition(records, counts)
    print()
    pprint_as_dicts(small)
    pprint_as_tuples(large)


def partition(records, counts, threshold=3):
    small, large = [], []
    for record in records:
        if counts[record.name] <= threshold:
            small.append(record)
        else:
            large.append(record)
    return small, large


def pprint_as_dicts(records):
    for record in records:
        if record.is_known():
            record = record.as_dict(filter=chain(append_units, fix_degrees, no_unknown, no_nulls))
            print(record.name)
            pprint_with_tabs('%s: %s' % (name, value) for name, value in sorted(record.data.items()))
            print()


def pprint_as_tuples(records):
    records = [record.force() for record in records]
    for record in records:
        t = record.as_names(filter=chain(no_unknown, no_nulls))
        v = record.as_values(filter=chain(append_units, fix_degrees, no_unknown, no_nulls))
        if len(t.data) != len(v.data):
            print(t)
            print(v)
            print(record.as_dict())
            raise Exception()
    titles = [record.as_names(filter=chain(no_unknown, no_nulls))
              for record in unique(records, key=lambda x: x.name)
              if record.is_known()]
    for title in titles:
        pprint_series(title, [record.as_values(filter=chain(append_units, fix_degrees, no_unknown, no_nulls))
                              for record in records
                              if record.name == title.name])


def measure_lengths(records, lengths=None, separator=','):
    for record in records:
        if lengths is None:
            lengths = [len(datum) + (len(separator) if i+1 < len(record.data) else 0)
                       for i, datum in enumerate(record.data)]
        else:
            for i, l in ((i, len(datum) + (len(separator) if i+1 < len(record.data) else 0))
                         for i, datum in enumerate(record.data)):
                lengths[i] = max(lengths[i], l)
    return lengths


def pad_to_lengths(record, lengths, separator=','):
    for i, datum in enumerate(record.data):
        yield (datum + (separator if i+1 < len(lengths) else '')).ljust(lengths[i])


def pprint_series(title, records):
    print(title.name)
    print(title.data)
    for record in records:
        print(record.data)
    lengths = measure_lengths(records, lengths=measure_lengths([title]))
    pprint_with_tabs(pad_to_lengths(title, lengths), separator='')
    for record in records:
        pprint_with_tabs(pad_to_lengths(record, lengths), separator='')
    print()


def pprint_with_tabs(data, indent=2, tab=4, width=79, separator=','):
    line = ' ' * indent
    first = True
    for datum in data:
        if not first:
            line += separator
        l_old = len(line)
        if l_old > indent:
            l_new = (1 + (l_old - indent + 1) // tab) * tab + indent
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
